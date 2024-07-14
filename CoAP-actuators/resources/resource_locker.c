#include "contiki.h"
#include "coap-engine.h"
#include "os/dev/leds.h"
#include "../cJSON-master/cJSON.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>


/* ---------------------------------------------- */
/*               Log configuration                */
/* ---------------------------------------------- */

#include "sys/log.h"
#define LOG_MODULE "Locker - resource"
#define LOG_LEVEL LOG_LEVEL_INFO


/* ---------------------------------------------- */
/*              Status configuration              */
/* ---------------------------------------------- */

// Locker status enumeration
typedef enum {
    LOCKER_OFF = 0,
    LOCKER_ON = 1
} locker_status_t;

// String representation of the locker status
const char* getLockerStatus(locker_status_t status){
    switch(status){
        case LOCKER_OFF:
            return "off";
        case LOCKER_ON:
            return "on";
        default:
            return "unknown";
    }
}

// Initial status
static locker_status_t locker_status = LOCKER_OFF;


/* ---------------------------------------------- */
/*             Resource configuration             */
/* ---------------------------------------------- */

// Handler declaration for PUT request
static void res_put_handler(coap_message_t *request, coap_message_t *response, uint8_t *buffer, uint16_t preferred_size, int32_t *offset);

// Resource definition
RESOURCE(res_locker,
         "title=\"LEATHERSENSE: ?actuator_locker=<string>\";action=<action>\";rt=\"Control\";if=\"actuator\"",
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
        cJSON *root = cJSON_ParseWithLength((const char *)chunk, len);
        if(root == NULL) {
            LOG_ERR("Failed to parse JSON\n");
            coap_set_status_code(response, BAD_REQUEST_4_00);
            return;
        }
        action = cJSON_GetObjectItem(root, "action")->valuestring;
        LOG_INFO("received command: action=%s\n", action);
	}

    // Check the action and set the locker status accordingly
    if(action!=NULL && strlen(action)!=0){

        // LOCKER_OFF -> GREEN led
        if((strncmp(action, getLockerStatus(LOCKER_OFF), len) == 0)){
            if(locker_status != LOCKER_OFF){
                locker_status = LOCKER_OFF;
                leds_off(LEDS_RED);
                leds_off(LEDS_BLUE);
                leds_on(LEDS_GREEN);
                LOG_INFO("Locker is off\n");
            }
            else
                LOG_WARN("Locker is already off\n");

		    coap_set_status_code(response, CHANGED_2_04);
	    }

        // LOCKER_ON -> RED led
        else if((strncmp(action, getLockerStatus(LOCKER_ON), len) == 0)){
            if(locker_status != LOCKER_ON){
                locker_status = LOCKER_ON;
                leds_off(LEDS_BLUE);
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                LOG_INFO("Locker is active\n");
            }
            else
                LOG_WARN("Locker is already active\n");

            coap_set_status_code(response, CHANGED_2_04);
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