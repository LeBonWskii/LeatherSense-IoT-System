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

#include <string.h>
#include <strings.h>
/*---------------------------------------------------------------------------*/
#define LOG_MODULE "sensor-temp_ph_sal"
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

// We assume that the broker does not require authentication

/*---------------------------------------------------------------------------*/
/* Various states */
static uint8_t state;

#define STATE_INIT    		          0
#define STATE_NET_OK    	          1
#define STATE_CONNECTING            2
#define STATE_CONNECTED             3
#define STATE_WAITSUBACKTEMP        4
#define STATE_SUBSCRIBEDTEMP        5
#define STATE_WAITSUBACKPH          6
#define STATE_SUBSCRIBEDPH          7
#define STATE_WAITSUBACKSAL         8
#define STATE_SUBSCRIBEDALL         9
#define STATE_DISCONNECTED          10

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
static char sub_topic[BUFFER_SIZE];


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

/*variables to report values outside the limits */
static bool temp_out_of_bounds = false;
static bool ph_out_of_bounds = false;
static bool salinity_out_of_bounds = false;

/*variables for sensing treshold*/
static int max_temp_treshold = 30;
static int min_temp_treshold = 10;
static int max_ph_treshold = 8;
static int min_ph_treshold = 6;
static int max_salinity_treshold = 35;
static int min_salinity_treshold = 30;

/*variables for sensing values*/
static int current_temp = 0;
static int current_ph = 0;
static int current_salinity = 0;

/* Array of topics to subscribe to */
static const char* topics[] = {"param/temp", "param/ph", "param/sal"}; 
#define NUM_TOPICS 3
static int current_topic_index = 0; // Index of the current topic being subscribed to

static struct ctimer tps_sensor_timer; //timer for periodic sensing values of temperature, pH and salinity
static bool first_time = true; //flag to check if it is the first time the sensor is activated

#define SENSOR_INTERVAL (CLOCK_SECOND * 20) //interval for sensing values of temperature, pH and salinity
/*---------------------------------------------------------------------------*/
/*Utility functions for generate random sensing values*/

static int generate_random_temp(){
    return (rand() % (max_temp_treshold - min_temp_treshold + 1)) + min_temp_treshold;
} 

static int generate_random_ph(){
    return (rand() % (max_ph_treshold - min_ph_treshold + 1)) + min_ph_treshold;
}

static int generate_random_salinity(){
    return (rand() % (max_salinity_treshold - min_salinity_treshold + 1)) + min_salinity_treshold;
}

/*---------------------------------------------------------------------------*/
static void sensor_callback(void *ptr){
    if(state != STATE_SUBSCRIBEDALL) // Check if the sensor is subscribed to all topics
        return;
    leds_on(LEDS_NUM_TO_MASK(LEDS_GREEN)); //turn on green led to signal the sensing

    // Generate random values for temperature, pH and salinity
    current_temp = generate_random_temp();
    current_ph = generate_random_ph();
    current_salinity = generate_random_salinity();

    LOG_INFO("Sensing finished: temperature: %d, pH: %d, salinity: %d\n", current_temp, current_ph, current_salinity);

    // Check if the values are within the limits
    if(current_temp < min_temp_treshold || current_temp > max_temp_treshold)
        temp_out_of_bounds = true;
    else
        temp_out_of_bounds = false;

    if(current_ph < min_ph_treshold || current_ph > max_ph_treshold)
        ph_out_of_bounds = true;
    else
        ph_out_of_bounds = false;

    if(current_salinity < min_salinity_treshold || current_salinity > max_salinity_treshold)
        salinity_out_of_bounds = true;
    else
        salinity_out_of_bounds = false;

    // Publish the values
    sprintf(pub_topic, "%s", "sensor/temp_pH_sal"); //publish on the topic sensor/temp_pH_sal
    sprintf(app_buffer, "{ \"temperature\": %d, \"pH\": %d, \"salinity\": %d }", current_temp, current_ph, current_salinity);
    mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
    LOG_INFO("Publishing values on %s topic\n", pub_topic);
    leds_off(LEDS_NUM_TO_MASK(LEDS_GREEN)); //turn off green led to signal the end of the sensing
    // Set the timer for the next sensing
    ctimer_reset(&tps_sensor_timer);

}
/*---------------------------------------------------------------------------*/
PROCESS(sensor_temp_ph_sal, "MQTT sensor_temperature_pH_sal");
AUTOSTART_PROCESSES(&sensor_temp_ph_sal);

/*---------------------------------------------------------------------------*/
/*Handler to manage the setting of parameters in case of publication on the topic to which the sensor is subscribed*/
static void
pub_handler_temp(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    // Handle temperature settings
}
static void
pub_handler_ph(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    // Handle pH settings
}
static void
pub_handler_sal(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    // Handle salinity settings
}

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
    process_poll(&sensor_temp_ph_sal);
    break;
  }
  case MQTT_EVENT_PUBLISH: {
    msg_ptr = data;

    if(strcmp(msg_ptr->topic, "param/temp") == 0)
        pub_handler_temp(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    else if(strcmp(msg_ptr->topic, "param/ph") == 0)
        pub_handler_ph(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    else if(strcmp(msg_ptr->topic, "param/sal") == 0)
        pub_handler_sal(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    break;
  }
  case MQTT_EVENT_SUBACK: {
#if MQTT_311
    mqtt_suback_event_t *suback_event = (mqtt_suback_event_t *)data;

    if(suback_event->success) {
      LOG_INFO("Application is subscribed to topic successfully\n");
      current_topic_index++; // Move to the next topic after a successful subscription
    } else {
      LOG_INFO("Application failed to subscribe to topic (ret code %x)\n", suback_event->return_code);
    }
#else
    LOG_INFO("Application is subscribed to topic successfully\n");
    current_topic_index++; // Move to the next topic after a successful subscription
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
PROCESS_THREAD(sensor_temp_ph_sal, ev, data)
{
  PROCESS_BEGIN();
  
  LOG_INFO("MQTT-Sensor-temp_ph_salinity started\n");

  // Initialize the ClientID as MAC address
  snprintf(client_id, BUFFER_SIZE, "%02x%02x%02x%02x%02x%02x",
                     linkaddr_node_addr.u8[0], linkaddr_node_addr.u8[1],
                     linkaddr_node_addr.u8[2], linkaddr_node_addr.u8[5],
                     linkaddr_node_addr.u8[6], linkaddr_node_addr.u8[7]);

  // Broker registration
  mqtt_register(&conn, &sensor_temp_ph_sal, client_id, mqtt_event, MAX_TCP_SEGMENT_SIZE);
  
  state = STATE_INIT;
  current_topic_index = 0;

  // Initialize periodic timer to check the status 
  etimer_set(&periodic_timer, STATE_MACHINE_PERIODIC);

  /* Main loop */
  while (1) {
    PROCESS_YIELD();

    if ((ev == PROCESS_EVENT_TIMER && data == &periodic_timer) || ev == PROCESS_EVENT_POLL) {
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
        // Start subscribing to topics
        strcpy(sub_topic, topics[current_topic_index]);
        status=mqtt_subscribe(&conn, NULL, sub_topic, MQTT_QOS_LEVEL_0);
        LOG_INFO("Subscribing to %s topic!\n", sub_topic);
        if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
            LOG_ERR("Tried to subscribe to %s topic but command queue was full!\n", sub_topic);
            PROCESS_EXIT();
        }
        state = STATE_WAITSUBACKTEMP;
      }

      if(state == STATE_WAITSUBACKTEMP && current_topic_index == 1)
            state = STATE_SUBSCRIBEDTEMP;

        if(state == STATE_SUBSCRIBEDTEMP){
        strcpy(sub_topic, topics[current_topic_index]);
        status=mqtt_subscribe(&conn, NULL, sub_topic, MQTT_QOS_LEVEL_0);
        LOG_INFO("Subscribing to %s topic!\n", sub_topic);
        if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
            LOG_ERR("Tried to subscribe to %s topic but command queue was full!\n", sub_topic);
            PROCESS_EXIT();
        }
        state = STATE_WAITSUBACKPH;
      }

    if(state == STATE_WAITSUBACKPH && current_topic_index == 2)
            state = STATE_SUBSCRIBEDPH;
    
    if(state == STATE_SUBSCRIBEDPH){
        strcpy(sub_topic, topics[current_topic_index]);
        status=mqtt_subscribe(&conn, NULL, sub_topic, MQTT_QOS_LEVEL_0);
        LOG_INFO("Subscribing to %s topic!\n", sub_topic);
        if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
            LOG_ERR("Tried to subscribe to %s topic but command queue was full!\n", sub_topic);
            PROCESS_EXIT();
        }
        state = STATE_WAITSUBACKSAL;
      }
    
    if(state == STATE_WAITSUBACKSAL && current_topic_index == 3)
            state = STATE_SUBSCRIBEDALL;
      
      // Handle subscription states
      if (state == STATE_SUBSCRIBEDALL) {
        // Start the timer for sensing values
        if(first_time){
            ctimer_set(&tps_sensor_timer, SENSOR_INTERVAL, sensor_callback, NULL);
            first_time = false;
        }
      } else if (state == STATE_DISCONNECTED) {
        LOG_ERR("Disconnected from MQTT broker\n");
        // Recover from error
      }
      
      etimer_set(&periodic_timer, STATE_MACHINE_PERIODIC);
    }
  }

  PROCESS_END();
}
