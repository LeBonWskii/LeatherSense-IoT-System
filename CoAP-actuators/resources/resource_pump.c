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
#define LOG_MODULE "Pump - resource"
#define LOG_LEVEL LOG_LEVEL_INFO


/* ---------------------------------------------- */
/*              Status configuration              */
/* ---------------------------------------------- */

// Pump status enumeration
typedef enum {
    PUMP_OFF = 0,
    PUMP_PURE = 7,
    PUMP_ACID = 1,
    PUMP_BASE = 14
} pump_status_t;

// String representation of the pump status
const char* getPumpStatus(pump_status_t status){
    switch(status){
        case PUMP_OFF:
            return "off";
        case PUMP_PURE:
            return "pure";
        case PUMP_ACID:
            return "acid";
        case PUMP_BASE:
            return "base";
        default:
            return "unknown";
    }
}

// Initial status
static pump_status_t pump_status = PUMP_OFF;


/* ---------------------------------------------- */
/*             Resource configuration             */
/* ---------------------------------------------- */

// Handler declaration for PUT request
static void res_put_handler(coap_message_t *request, coap_message_t *response, uint8_t *buffer, uint16_t preferred_size, int32_t *offset);

// Resource definition
RESOURCE(res_pump,
         "title=\"LEATHERSENSE: ?actuator_pump=<string>\";action=<action>\";rt=\"Control\";if=\"actuator\"",
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

    // Check the action and set the pump status accordingly
    if(action!=NULL && strlen(action)!=0){

        // PUMP_OFF -> GREEN led
        if((strncmp(action, getPumpStatus(PUMP_OFF), len) == 0)){
            if(pump_status != PUMP_OFF){
                pump_status = PUMP_OFF;
                leds_off(LEDS_RED);
                leds_off(LEDS_BLUE);
                leds_on(LEDS_GREEN);
                LOG_INFO("Pump is off\n");
            }
            else
                LOG_WARN("Pump is already off\n");

		    coap_set_status_code(response, CHANGED_2_04);
	    }

        //  PUMP_PURE -> BLUE led
        else if((strncmp(action, getPumpStatus(PUMP_PURE), len) == 0)){
            if(pump_status != PUMP_PURE){
                pump_status = PUMP_PURE;
                leds_on(LEDS_BLUE);
                leds_off(LEDS_GREEN);
                leds_off(LEDS_RED);
                LOG_INFO("Pump is in pure mode\n");
            }
            else
                LOG_WARN("Pump is already in pure mode\n");
            
            coap_set_status_code(response, CHANGED_2_04);
        }

        // PUMP_ACID -> RED led
        else if((strncmp(action, getPumpStatus(PUMP_ACID), len) == 0)){
            if(pump_status != PUMP_ACID){
                pump_status = PUMP_ACID;
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                leds_off(LEDS_BLUE);
                LOG_INFO("Pump is in acid mode\n");
            }
            else
                LOG_WARN("Pump is already in acid mode\n");
            
            coap_set_status_code(response, CHANGED_2_04);
        }

        // PUMP_BASE -> BLUE + RED leds (PURPLE)
        else if((strncmp(action, getPumpStatus(PUMP_BASE), len) == 0)){
            if(pump_status != PUMP_BASE){
                pump_status = PUMP_BASE;
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                leds_on(LEDS_BLUE);
                LOG_INFO("Pump is in base mode\n");
            }
            else
                LOG_WARN("Pump is already in base mode\n");
            
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