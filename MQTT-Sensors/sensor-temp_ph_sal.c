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
#include <stdbool.h>
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
#define RECONNECT_DELAY_MS (CLOCK_SECOND * 5) 


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
#define STATE_SUBSCRIBEDSAL         9
#define STATE_WAITSTART             10
#define STATE_START                 11
#define STATE_STOP                  12
#define STATE_DISCONNECTED          13

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
static bool ph_out_of_bounds_min = false;
static bool ph_out_of_bounds_max = false;
static bool salinity_out_of_bounds_min = false;
static bool salinity_out_of_bounds_max = false;

/*variables for sensing threshold*/
static double max_temp_threshold = 25;
static double min_ph_threshold = 2.8;
static double max_ph_threshold = 3;
static double min_salinity_threshold = 2;
static double max_salinity_threshold = 3;
static double delta_temp = 5;
static double delta_ph = 0.1;
static double delta_salinity = 0.5;

/*variables for sensing values*/
static double current_temp = 0;
static double current_ph = 0;
static double current_salinity = 0;

/* Array of topics to subscribe to */
static const char* topics[] = {"params/temperature", "params/ph", "params/salinity", "pickling"}; 
#define NUM_TOPICS 3
static int current_topic_index = 0; // Index of the current topic being subscribed to
static int count_sensor_interval = 0;//counter to check the number of times the sensor is activated
static bool warning_status_active = false; //flag to check if the warning is active
static bool start = false; //flag to check if the pickling process is started. 

static char payload[BUFFER_SIZE];


static struct ctimer tps_sensor_timer; //timer for periodic sensing values of temperature, pH and salinity
static bool first_time = true; //flag to check if it is the first time the sensor is activated
static struct etimer reconnection_timer; //timer for reconnection to the broker

#define SENSOR_INTERVAL (CLOCK_SECOND * 10) //interval for sensing values of temperature, pH and salinity
#define MONITORING_INTERVAL (CLOCK_SECOND * 5) //interval for monitoring the values of temperature, pH and salinity if they are out of bounds

/*---------------------------------------------------------------------------*/
/*Utility functions for generate random sensing values*/

static double generate_random_temp() {
    
    double random_fraction = (double)rand() / RAND_MAX;

    
    if ((rand() % 100) < 80) 
      return 5 + random_fraction * (max_temp_threshold - 5);
    else 
      return (max_temp_threshold + 1) + random_fraction * (delta_temp + 1);
    
}


static double generate_random_ph() {
    
    double random_fraction = (double)rand() / RAND_MAX;

    return min_ph_threshold + random_fraction * (max_ph_threshold - min_ph_threshold);
}


static double generate_random_salinity() {
    
    double random_fraction = (double)rand() / RAND_MAX;

    return min_salinity_threshold + random_fraction * (max_salinity_threshold - min_salinity_threshold);
}

void replace_comma_with_dot(char *str) {
    char *ptr = str;
    while (*ptr != '\0') {
        if (*ptr == ',') {
            *ptr = '.';
        }
        ptr++;
    }
}

/*---------------------------------------------------------------------------*/
static void sensor_callback(void *ptr){
    if(state != STATE_START) 
        return;

    // Generate random values for temperature, pH and salinity
    current_temp = generate_random_temp();
    current_ph = generate_random_ph();
    current_salinity = generate_random_salinity();

    LOG_INFO("Sensing finished: temperature: %f, pH: %f, salinity: %f\n", current_temp, current_ph, current_salinity);

    if(!warning_status_active){
      if(current_temp > max_temp_threshold)
          temp_out_of_bounds = true;
      else
          temp_out_of_bounds = false;

      if(current_ph < min_ph_threshold)
          ph_out_of_bounds_min = true;
      else if(current_ph > max_ph_threshold)
          ph_out_of_bounds_max = true;
      else{
          ph_out_of_bounds_min = false;
          ph_out_of_bounds_max = false;
      }

      if(current_salinity < min_salinity_threshold)
          salinity_out_of_bounds_min = true;
      else if(current_salinity > max_salinity_threshold)
          salinity_out_of_bounds_max = true;
      else{
          salinity_out_of_bounds_min = false;
          salinity_out_of_bounds_max = false;
      }

          
    }
    



    if(warning_status_active){

      if(temp_out_of_bounds && current_temp <= max_temp_threshold - delta_temp)
          temp_out_of_bounds = false;

      if(ph_out_of_bounds_min && current_ph >= min_ph_threshold + delta_ph)
          ph_out_of_bounds_min = false;

      if(ph_out_of_bounds_max && current_ph <= max_ph_threshold - delta_ph)
          ph_out_of_bounds_max = false;

      if(salinity_out_of_bounds_min && current_salinity >= min_salinity_threshold + delta_salinity)
          salinity_out_of_bounds_min = false;

      if(salinity_out_of_bounds_max && current_salinity <= max_salinity_threshold - delta_salinity)
          salinity_out_of_bounds_max = false;
    


      /*if all values are in the range [min_value + delta ; maxvalue] or [minvalue ; max_value - delta] then publish data and set warning status off*/
      if (!temp_out_of_bounds && (!ph_out_of_bounds_min && !ph_out_of_bounds_max) && (!salinity_out_of_bounds_min && !salinity_out_of_bounds_max)) {
          sprintf(pub_topic, "%s", "sensor/temp_pH_sal"); // publish on the topic sensor/temp_pH_sal

          cJSON *root = cJSON_CreateObject();
          if (!root) {
              printf("Error creating cJSON object.\n");
              return;  
          }

          // Convert numeric values to strings
          char temp_str[20]; // Adjust size based on your maximum expected length
          char ph_str[20];
          char salinity_str[20];
          sprintf(temp_str, "%.2f", current_temp);
          sprintf(ph_str, "%.2f", current_ph);
          sprintf(salinity_str, "%.2f", current_salinity);

          // Add temperature, pH, and salinity values as strings to cJSON object
          cJSON_AddStringToObject(root, "temperature", temp_str);
          cJSON_AddStringToObject(root, "pH", ph_str);
          cJSON_AddStringToObject(root, "salinity", salinity_str);

          char *json_string = cJSON_PrintUnformatted(root); 
          if (!json_string) {
              cJSON_Delete(root);
              printf("Error converting cJSON object to JSON string.\n");
              return;  
          }

          sprintf(app_buffer, "%s", json_string);

          // Cleanup cJSON resources
          cJSON_Delete(root);
          free(json_string);

          // Publish JSON string
          mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
          LOG_INFO("Publishing values on %s topic. Publishing reason: warning status disabled\n", pub_topic);

          // Reset variables and set timer
          warning_status_active = false;
          count_sensor_interval = 0;
          ctimer_set(&tps_sensor_timer, SENSOR_INTERVAL, sensor_callback, NULL);
      }

        /*else if values are not in range publish only after 3 times (15 seconds in warning status)*/
      else if(count_sensor_interval == 2){
              sprintf(pub_topic, "%s", "sensor/temp_pH_sal"); // publish on the topic sensor/temp_pH_sal

              cJSON *root = cJSON_CreateObject();
              if (!root) {
                  printf("Error creating cJSON object.\n");
                  return;  
              }

              // Convert numeric values to strings
              char temp_str[20]; // Adjust size based on your maximum expected length
              char ph_str[20];
              char salinity_str[20];
              sprintf(temp_str, "%.2f", current_temp);
              sprintf(ph_str, "%.2f", current_ph);
              sprintf(salinity_str, "%.2f", current_salinity);

              // Add temperature, pH, and salinity values as strings to cJSON object
              cJSON_AddStringToObject(root, "temperature", temp_str);
              cJSON_AddStringToObject(root, "pH", ph_str);
              cJSON_AddStringToObject(root, "salinity", salinity_str);

              char *json_string = cJSON_PrintUnformatted(root); 
              if (!json_string) {
                  cJSON_Delete(root);
                  printf("Error converting cJSON object to JSON string.\n");
                  return;  
              }

              sprintf(app_buffer, "%s", json_string);

              // Cleanup cJSON resources
              cJSON_Delete(root);
              free(json_string);

              // Publish JSON string
              mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
              LOG_INFO("Publishing values on %s topic. Publishing reason: too much time spent without publishin in warning status\n", pub_topic);
              count_sensor_interval = 0;
              ctimer_reset(&tps_sensor_timer);
        }
        else{
            count_sensor_interval++;
            ctimer_reset(&tps_sensor_timer);
        }
    }   
    
    else{
      /*if are detected values out of bounds for the first time then publish data and set warning status on*/
        if(temp_out_of_bounds || ph_out_of_bounds_min || ph_out_of_bounds_max || salinity_out_of_bounds_min || salinity_out_of_bounds_max){
              sprintf(pub_topic, "%s", "sensor/temp_pH_sal"); // publish on the topic sensor/temp_pH_sal

              cJSON *root = cJSON_CreateObject();
              if (!root) {
                  printf("Error creating cJSON object.\n");
                  return;  
              }

              // Convert numeric values to strings
              char temp_str[20]; // Adjust size based on your maximum expected length
              char ph_str[20];
              char salinity_str[20];
              sprintf(temp_str, "%.2f", current_temp);
              sprintf(ph_str, "%.2f", current_ph);
              sprintf(salinity_str, "%.2f", current_salinity);

              // Add temperature, pH, and salinity values as strings to cJSON object
              cJSON_AddStringToObject(root, "temperature", temp_str);
              cJSON_AddStringToObject(root, "pH", ph_str);
              cJSON_AddStringToObject(root, "salinity", salinity_str);

              char *json_string = cJSON_PrintUnformatted(root); 
              if (!json_string) {
                  cJSON_Delete(root);
                  printf("Error converting cJSON object to JSON string.\n");
                  return;  
              }

              sprintf(app_buffer, "%s", json_string);

              // Cleanup cJSON resources
              cJSON_Delete(root);
              free(json_string);

              // Publish JSON string
              mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
              LOG_INFO("Publishing values on %s topic. Publishing reason: detected values out of bounds\n", pub_topic);
              warning_status_active = true;
              count_sensor_interval = 0;
              ctimer_set(&tps_sensor_timer, MONITORING_INTERVAL, sensor_callback, NULL);
        }
        else{
          /*else all is ok publish only after 4 times (40 seconds in normal status)*/
            if(count_sensor_interval == 3){
                sprintf(pub_topic, "%s", "sensor/temp_pH_sal"); // publish on the topic sensor/temp_pH_sal

                cJSON *root = cJSON_CreateObject();
                if (!root) {
                    printf("Error creating cJSON object.\n");
                    return;  
                }

                // Convert numeric values to strings
                char temp_str[20]; // Adjust size based on your maximum expected length
                char ph_str[20];
                char salinity_str[20];
                sprintf(temp_str, "%.2f", current_temp);
                sprintf(ph_str, "%.2f", current_ph);
                sprintf(salinity_str, "%.2f", current_salinity);

                // Add temperature, pH, and salinity values as strings to cJSON object
                cJSON_AddStringToObject(root, "temperature", temp_str);
                cJSON_AddStringToObject(root, "pH", ph_str);
                cJSON_AddStringToObject(root, "salinity", salinity_str);

                char *json_string = cJSON_PrintUnformatted(root); 
                if (!json_string) {
                    cJSON_Delete(root);
                    printf("Error converting cJSON object to JSON string.\n");
                    return;  
                }

                sprintf(app_buffer, "%s", json_string);

                // Cleanup cJSON resources
                cJSON_Delete(root);
                free(json_string);

                // Publish JSON string
                mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer, strlen(app_buffer), MQTT_QOS_LEVEL_1, MQTT_RETAIN_OFF);
                LOG_INFO("Publishing values on %s topic. Publishing reason: too much time spent without publishing in normal status\n", pub_topic);
                count_sensor_interval = 0;
                ctimer_reset(&tps_sensor_timer);
            }
            else{
                count_sensor_interval++;
                ctimer_reset(&tps_sensor_timer);
            }
        }
    }
}
  


/*---------------------------------------------------------------------------*/
PROCESS(sensor_temp_ph_sal, "MQTT sensor_temperature_pH_sal");
AUTOSTART_PROCESSES(&sensor_temp_ph_sal);

/*---------------------------------------------------------------------------*/
/*Handler to manage the setting of parameters in case of publication on the topic to which the sensor is subscribed*/
static void pub_handler_start(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    memcpy(payload, chunk, chunk_len);
    payload[chunk_len] = '\0';
    cJSON *json = cJSON_Parse(payload);
    cJSON *str = cJSON_GetObjectItem(json, "value");
    if(str){
        if(state == STATE_WAITSTART && strcmp(str->valuestring, "start") == 0){
            LOG_INFO("Start pickling process\n");
            state = STATE_START;
        }
        else if(state == STATE_START && strcmp(str->valuestring, "stop") == 0){
            LOG_INFO("Stop pickling process\n");
            state = STATE_STOP;
        }
    }
}

static void pub_handler_temp(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    memcpy(payload, chunk, chunk_len);
    payload[chunk_len] = '\0';
    cJSON *json = cJSON_Parse(payload);
    cJSON *max = cJSON_GetObjectItem(json, "max_value");
    cJSON *delta = cJSON_GetObjectItem(json, "delta");
    
    if(max){
        LOG_INFO("Temperature maximum value threshold set from %f to %f\n", max_temp_threshold, max->valuedouble);
        max_temp_threshold = max->valuedouble;
    }

    if(delta){
        LOG_INFO("Temperature delta value set from %f to %f\n", delta_temp, delta->valuedouble);
        delta_temp = delta->valuedouble;
    }


}
static void pub_handler_ph(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    memcpy(payload, chunk, chunk_len);
    payload[chunk_len] = '\0';
    cJSON *json = cJSON_Parse(payload);
    cJSON *min = cJSON_GetObjectItem(json, "min_value");
    cJSON *max = cJSON_GetObjectItem(json, "max_value");
    cJSON *delta = cJSON_GetObjectItem(json, "delta");

    if(min){
        LOG_INFO("pH minimum value threshold set from %f to %f\n", min_ph_threshold, min->valuedouble);
        min_ph_threshold = min->valuedouble;
    }

    if(max){
        LOG_INFO("pH maximum value threshold set from %f to %f\n", max_ph_threshold, max->valuedouble);
        max_ph_threshold = max->valuedouble;
    }

    if(delta){
        LOG_INFO("pH delta value set from %f to %f\n", delta_ph, delta->valuedouble);
        delta_ph = delta->valuedouble;
    }

    
}
static void pub_handler_sal(const char *topic, uint16_t topic_len, const uint8_t *chunk, uint16_t chunk_len){
    memcpy(payload, chunk, chunk_len);
    payload[chunk_len] = '\0';
    cJSON *json = cJSON_Parse(payload);
    cJSON *min = cJSON_GetObjectItem(json, "min_value");
    cJSON *max = cJSON_GetObjectItem(json, "max_value");
    cJSON *delta = cJSON_GetObjectItem(json, "delta");

    if(min){
        LOG_INFO("Salinity minimum value threshold set from %f to %f\n", min_salinity_threshold, min->valuedouble);
        min_salinity_threshold = min->valuedouble;
    }

    if(max){
        LOG_INFO("Salinity maximum value threshold set from %f to %f\n", max_salinity_threshold, max->valuedouble);
        max_salinity_threshold = max->valuedouble;
    }

    if(delta){
        LOG_INFO("Salinity delta value set from %f to %f\n", delta_salinity, delta->valuedouble);
        delta_salinity = delta->valuedouble;
    }

}

/*---------------------------------------------------------------------------*/
static void mqtt_event(struct mqtt_connection *m, mqtt_event_t event, void *data){
  switch(event) {
  case MQTT_EVENT_CONNECTED: {
    LOG_INFO("Application has a MQTT connection\n");
    state = STATE_CONNECTED;
    current_topic_index = 0;
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

    if(strcmp(msg_ptr->topic, "params/temperature") == 0)
        pub_handler_temp(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    else if(strcmp(msg_ptr->topic,"params/ph") == 0)
        pub_handler_ph(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    else if(strcmp(msg_ptr->topic, "params/salinity") == 0)
        pub_handler_sal(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
    else if (strcmp(msg_ptr->topic, "pickling") == 0)
        pub_handler_start(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_chunk, msg_ptr->payload_length);
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
            state = STATE_SUBSCRIBEDSAL;
    
    if(state == STATE_SUBSCRIBEDSAL){
        strcpy(sub_topic, topics[current_topic_index]);
        status=mqtt_subscribe(&conn, NULL, sub_topic, MQTT_QOS_LEVEL_0);
        LOG_INFO("Subscribing to %s topic!\n", sub_topic);
        if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
            LOG_ERR("Tried to subscribe to %s topic but command queue was full!\n", sub_topic);
            PROCESS_EXIT();
        }
        if(!start){
            state = STATE_WAITSTART;
            LOG_INFO("Waiting for start command for temp_ph_sal sensor\n");
        }
        else{
            state = STATE_START;
            first_time = true;
        }
      }
    
        
     
      if (state == STATE_START) {
        // Start the timer for sensing values
        if(first_time){
            ctimer_set(&tps_sensor_timer, SENSOR_INTERVAL, sensor_callback, NULL);
            first_time = false;
            start=true;
            LOG_INFO("Sensor temp_ph_sal started successfully\n");
        }
      } 
      else if (state == STATE_STOP){
        ctimer_stop(&tps_sensor_timer);
        first_time = true;
        temp_out_of_bounds = false;
        ph_out_of_bounds_min = false;
        ph_out_of_bounds_max = false;
        salinity_out_of_bounds_min = false;
        salinity_out_of_bounds_max = false;
        warning_status_active = false;
        count_sensor_interval = 0;
        state = STATE_WAITSTART;
        start = false;
         LOG_INFO("Sensor temp_ph_sal stopped successfully\n");
      }
       else if (state == STATE_DISCONNECTED) {
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
