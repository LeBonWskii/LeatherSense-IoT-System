#include "contiki.h"
#include "coap-engine.h"
#include "os/dev/leds.h"
#include "json_util.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>


/* ---------------------------------------------- */
/*               Log configuration                */
/* ---------------------------------------------- */

#include "sys/log.h"
#define LOG_MODULE "App"
#define LOG_LEVEL LOG_LEVEL_INFO


/* ---------------------------------------------- */
/*              Status configuration              */
/* ---------------------------------------------- */

// Alarm status enumeration
typedef enum {
    ALARM_OFF = 0,
    ALARM_ON = 1
} alarm_status_t;

// String representation of the alarm status
const char* getAlarmStatus(alarm_status_t status){
    switch(status){
        case ALARM_OFF:
            return "off";
        case ALARM_ON:
            return "on";
        default:
            return "unknown";
    }
}

// Initial status
static alarm_status_t alarm_status = ALARM_OFF;


/* ---------------------------------------------- */
/*             Resource configuration             */
/* ---------------------------------------------- */

// Handler declaration for PUT request
static void res_put_handler(coap_message_t *request, coap_message_t *response, uint8_t *buffer, uint16_t preferred_size, int32_t *offset);

// Resource definition
RESOURCE(res_alarm,
         "title=\"LEATHERSENSE: ?actuator_alarm=<string>\" POST/PUTaction=<action>\";rt=\"Control\";if=\"actuator\"",
         NULL,
         NULL,
         res_put_handler,
         NULL);

// Handler implementation for PUT request
static void res_put_handler(coap_message_t *request, coap_message_t *response, uint8_t *buffer, uint16_t preferred_size, int32_t *offset){
    
    int len = 0;
    char* action = NULL;
    const uint8_t *chunk;
    
    len = coap_get_payload(request,&chunk);
	
    // Check if the payload is not empty and retrieve the action
    if(len>0){
        action = findJsonField_String((char *)chunk, "action");
        LOG_INFO("received command: action=%s\n", action);
	}

    // Check the action and set the alarm status accordingly
    if(action!=NULL && strlen(action)!=0){

        // ALARM_OFF -> GREEN led
        if((strncmp(action, getAlarmStatus(ALARM_OFF), len) == 0)){
            if(alarm_status != ALARM_OFF){
                alarm_status = ALARM_OFF;
                leds_off(LEDS_RED);
                leds_off(LEDS_BLUE);
                leds_on(LEDS_GREEN);
                LOG_INFO("Alarm is off\n");
            }
            else
                LOG_WARN("Alarm is already off\n");

		    coap_set_status_code(response, CHANGED_2_04);
	    }

        // ALARM_ON -> RED led
        else if((strncmp(action, getAlarmStatus(ALARM_ON), len) == 0)){
            if(alarm_status != ALARM_ON){
                alarm_status = ALARM_ON;
                leds_off(LEDS_BLUE);
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                LOG_INFO("Alarm is on\n");
            }
            else
                LOG_WARN("Alarm is already on\n");
        }

        // Invalid action, no change is performed
        else
            coap_set_status_code(response, BAD_OPTION_4_02);

    }

    // Invalid action, no change is performed
    else{
        coap_set_status_code(response, BAD_REQUEST_4_00);
    }

    free(action);
}