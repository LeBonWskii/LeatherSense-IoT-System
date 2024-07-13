/*
 * Copyright (c) 2020, Carlo Vallati, University of Pisa
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
 * COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */
/*---------------------------------------------------------------------------*/
#include "contiki.h"
#include "net/routing/routing.h"
#include "mqtt.h"
#include "net/ipv6/uip.h"
#include "net/ipv6/uip-icmp6.h"
#include "net/ipv6/sicslowpan.h"
#include "sys/etimer.h"
#include "sys/ctimer.h"
#include "lib/sensors.h"
#include "dev/button-hal.h"
#include "dev/leds.h"
#include "os/sys/log.h"
#include "mqtt-client.h"
#include "os/dev/button-hal.h"
#include "../cJSON-master/cJSON.h"

#include <string.h>
#include <strings.h>
/*---------------------------------------------------------------------------*/
#define LOG_MODULE "sensor_S02"
#ifdef MQTT_CLIENT_CONF_LOG_LEVEL
#define LOG_LEVEL MQTT_CLIENT_CONF_LOG_LEVEL
#else
#define LOG_LEVEL LOG_LEVEL_DBG
#endif

/*---------------------------------------------------------------------------*/
/* MQTT broker address. */
#define MQTT_CLIENT_BROKER_IP_ADDR "fd00::1"

static const char *broker_ip = MQTT_CLIENT_BROKER_IP_ADDR;

// Default config values
#define DEFAULT_BROKER_PORT         1883
#define DEFAULT_PUBLISH_INTERVAL    (30 * CLOCK_SECOND)
#define RECONNECT_DELAY_MS (CLOCK_SECOND * 5) 
// We assume that the broker does not require authentication

/*---------------------------------------------------------------------------*/
/* Various states */
static uint8_t state;

#define STATE_INIT    		          0
#define STATE_NET_OK    	          1
#define STATE_CONNECTING            2
#define STATE_CONNECTED             3
#define STATE_DISCONNECTED          4

//  STATE_SUBSCRIBEDTEMP. STATE_SUBSCRIBEDPH, STATE_SUBSCRIBEDSAL added only for major clarity but not required
/*---------------------------------------------------------------------------*/
/* Maximum TCP segment size for outgoing segments of our socket */
#define MAX_TCP_SEGMENT_SIZE    32
#define CONFIG_IP_ADDR_STR_LEN   64
/*---------------------------------------------------------------------------*/
/*
 * Buffers for Client ID and Topics.
 * Make sure they are large enough to hold the entire respective string
 */
#define BUFFER_SIZE 64

static char client_id[BUFFER_SIZE];
static char pub_topic[BUFFER_SIZE];



// Periodic timer to check the state of the MQTT client
#define STATE_MACHINE_PERIODIC     (CLOCK_SECOND >> 1)
static struct etimer periodic_timer;

/*---------------------------------------------------------------------------*/
/*
 * The main MQTT buffers.
 * We will need to increase if we start publishing more data.
 */
#define APP_BUFFER_SIZE 512
static char app_buffer[APP_BUFFER_SIZE];
/*---------------------------------------------------------------------------*/
static struct mqtt_message *msg_ptr = 0;

static struct mqtt_connection conn;

mqtt_status_t status;
char broker_address[CONFIG_IP_ADDR_STR_LEN];

/*---------------------------------------------------------------------------*/

/*Utility variables*/

/*variable for sensing values*/
static int current_so2 = 0;

static struct ctimer so2_sensor_timer; //timer for periodic sensing values of temperature, pH and salinity
static bool first_time = true; //flag to check if it is the first time the sensor is activated
static bool warning_status_active = false; //flag to check if the warning status is active
static int count_sensor_interval = 0; //counter for the number of times the sensor interval has been reached
static struct etimer reconnection_timer; //timer for reconnection to the broker

#define SENSOR_INTERVAL (CLOCK_SECOND * 8) //interval for sensing values of temperature, pH and salinity
#define MONITORING_INTERVAL (CLOCK_SECOND * 4) //interval for monitoring the is warning status
/*---------------------------------------------------------------------------*/
/*Utility function for generate random sensing values*/

static int generate_random_so2(){
    
   int r = rand() % 10;
        
    if (r < 8) 
        return 1;
     else 
        return 0;
    
} 


/*---------------------------------------------------------------------------*/
static void sensor_callback(void *ptr){
    // Generate random values for temperature, pH and salinity
    current_so2 = generate_random_so2();
    if(current_so2)
        LOG_INFO("*WARNING* SO2 DETECTED\n");
    else
        LOG_INFO("SO2 NOT DETECTED\n");
    if(warning_status_active){

        if(!current_so2){
            sprintf(pub_topic, "%s", "sensor/so2"); //publish on the topic sensor/so2
            sprintf(app_buffer, "{ \"so2\": %d }", current_so2);
            mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
            LOG_INFO("Publishing values on %s topic. Publishing reason: warning status disabled\n", pub_topic);
            warning_status_active = false;
            count_sensor_interval = 0;
            ctimer_set(&so2_sensor_timer, SENSOR_INTERVAL, sensor_callback, NULL);
        }
        /*else if values are not in range publish only after 3 times (15 seconds in warning status)*/
        else if(count_sensor_interval == 3){
            sprintf(pub_topic, "%s", "sensor/so2"); //publish on the topic sensor/so2
            sprintf(app_buffer, "{ \"so2\": %d }", current_so2);
            mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
            LOG_INFO("Publishing values on %s topic. Publishing reason: too much time spent without publishing in warning status\n", pub_topic);
            count_sensor_interval = 0;
            ctimer_reset(&so2_sensor_timer);
        }
        else{
            count_sensor_interval++;
            ctimer_reset(&so2_sensor_timer);
        }   
    }
    else{
      /*if are detected values out of bounds for the first time then publish data and set warning status on*/
        if(current_so2){
            sprintf(pub_topic, "%s", "sensor/so2"); //publish on the topic sensor/so2
            sprintf(app_buffer, "{ \"so2\": %d }", current_so2);
            mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
            LOG_INFO("Publishing values on %s topic. Publishing reason: values out of bounds\n", pub_topic);
            warning_status_active = true;
            count_sensor_interval = 0;
            ctimer_set(&so2_sensor_timer, MONITORING_INTERVAL, sensor_callback, NULL);
        }
        else{
          /*else all is ok publish only after 3 times (30 seconds in normal status)*/
            if(count_sensor_interval == 3){
                sprintf(pub_topic, "%s", "sensor/so2"); //publish on the topic sensor/so2
                sprintf(app_buffer, "{ \"so2\": %d }", current_so2);
                mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
                LOG_INFO("Publishing values on %s topic. Publishing reason: too much time spent without publishing in normal status\n", pub_topic);
                count_sensor_interval = 0;
                ctimer_reset(&so2_sensor_timer);
            }
            else{
                count_sensor_interval++;
                ctimer_reset(&so2_sensor_timer);
            }
        }
    }



}
/*---------------------------------------------------------------------------*/
PROCESS(sensor_so2, "MQTT sensor_so2");
AUTOSTART_PROCESSES(&sensor_so2);

/*---------------------------------------------------------------------------*/
static void mqtt_event(struct mqtt_connection *m, mqtt_event_t event, void *data){
  switch(event) {
  case MQTT_EVENT_CONNECTED: {
    LOG_INFO("Application has a MQTT connection\n");
    state = STATE_CONNECTED;
    break;
  }
  case MQTT_EVENT_DISCONNECTED: {
    LOG_INFO("MQTT Disconnect. Reason %u\n", *((mqtt_event_t *)data));
    state = STATE_DISCONNECTED;
    process_poll(&sensor_so2);
    break;
  }
  case MQTT_EVENT_PUBLISH: {
    msg_ptr = data;
   
    break;
  }
  case MQTT_EVENT_SUBACK: {
#if MQTT_311
    mqtt_suback_event_t *suback_event = (mqtt_suback_event_t *)data;

    if(suback_event->success) {
      LOG_INFO("Application is subscribed to topic successfully\n");
    } else {
      LOG_INFO("Application failed to subscribe to topic (ret code %x)\n", suback_event->return_code);
    }
#else
    LOG_INFO("Application is subscribed to topic successfully\n");
#endif
    
    break;
  }
  case MQTT_EVENT_UNSUBACK: {
    LOG_INFO("Application is unsubscribed to topic successfully\n");
    break;
  }
  case MQTT_EVENT_PUBACK: {
    LOG_INFO("Publishing complete.\n");
    break;
  }
  default:
    LOG_INFO("Application got a unhandled MQTT event: %i\n", event);
    break;
  }
}

static bool have_connectivity(void){
  if(uip_ds6_get_global(ADDR_PREFERRED) == NULL ||
     uip_ds6_defrt_choose() == NULL) {
    return false;
  }
  return true;
}

/*---------------------------------------------------------------------------*/
PROCESS_THREAD(sensor_so2, ev, data)
{
  PROCESS_BEGIN();
  
  LOG_INFO("MQTT-Sensor-SO2 started\n");

  // Initialize the ClientID as MAC address
  snprintf(client_id, BUFFER_SIZE, "%02x%02x%02x%02x%02x%02x",
                     linkaddr_node_addr.u8[0], linkaddr_node_addr.u8[1],
                     linkaddr_node_addr.u8[2], linkaddr_node_addr.u8[5],
                     linkaddr_node_addr.u8[6], linkaddr_node_addr.u8[7]);

  // Broker registration
  mqtt_register(&conn, &sensor_so2, client_id, mqtt_event, MAX_TCP_SEGMENT_SIZE);
  
  state = STATE_INIT;

  // Initialize periodic timer to check the status 
  etimer_set(&periodic_timer, STATE_MACHINE_PERIODIC);

  /* Main loop */
  while (1) {
    PROCESS_YIELD();

    if ((ev == PROCESS_EVENT_TIMER && data == &periodic_timer) || ev == PROCESS_EVENT_POLL || (ev == PROCESS_EVENT_TIMER && data == &reconnection_timer)) {
      if (state == STATE_INIT) {
        if (have_connectivity() == true)  
          state = STATE_NET_OK;
      } 
      
      if (state == STATE_NET_OK) {
        // Connect to MQTT server
        LOG_INFO("Connecting!\n");
        memcpy(broker_address, broker_ip, strlen(broker_ip));
        mqtt_connect(&conn, broker_address, DEFAULT_BROKER_PORT, (DEFAULT_PUBLISH_INTERVAL * 3) / CLOCK_SECOND, MQTT_CLEAN_SESSION_ON);
        state = STATE_CONNECTING;
      }
      

      if (state == STATE_CONNECTED) {
        // Start the timer for sensing values
        if(first_time){
            ctimer_set(&so2_sensor_timer, SENSOR_INTERVAL, sensor_callback, NULL);
            first_time = false;
        }
      } else if (state == STATE_DISCONNECTED) {
        LOG_ERR("Disconnected from MQTT broker\n");
        state = STATE_INIT;
        etimer_set(&reconnection_timer, RECONNECT_DELAY_MS);
        continue;

      }
      
      etimer_set(&periodic_timer, STATE_MACHINE_PERIODIC);
    }
  }

  PROCESS_END();
}
