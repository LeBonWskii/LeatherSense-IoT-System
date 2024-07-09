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

// Set the leds according to the pump status
void setPumpLeds(pump_status_t status){
    switch(status){
        case PUMP_OFF:  // GREEN
            leds_off(LEDS_RED);
            leds_off(LEDS_BLUE);
            leds_on(LEDS_GREEN);
            LOG_INFO("Pump is off\n");
            break;
        case PUMP_PURE: // YELLOW
            leds_off(LEDS_BLUE);
            leds_on(LEDS_GREEN);
            leds_on(LEDS_RED);
            LOG_INFO("Pump is in pure mode\n");
            break;
        case PUMP_ACID: // RED
            leds_off(LEDS_GREEN);
            leds_on(LEDS_RED);
            leds_off(LEDS_BLUE);
            LOG_INFO("Pump is in acid mode\n");
            break;
        case PUMP_BASE: // BLUE
            leds_off(LEDS_GREEN);
            leds_off(LEDS_RED);
            leds_on(LEDS_BLUE);
            LOG_INFO("Pump is in base mode\n");
            break;
        default:        // LEDS OFF
            leds_off(LEDS_GREEN);
            leds_off(LEDS_RED);
            leds_off(LEDS_BLUE);
            LOG_ERR("Pump status is unknown\n");
            break;
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
         "title=\"LEATHERSENSE: ?actuator_pump=0..\" POST/PUTaction=<action>\";rt=\"Control\";if=\"actuator\"",
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

    // Check the action and set the pump status accordingly
    if(action!=NULL && strlen(action)!=0){

        // PUMP_OFF
        if((strncmp(action, getPumpStatus(PUMP_OFF), len) == 0)){
            if(pump_status != PUMP_OFF){
                pump_status = PUMP_OFF;
                setPumpLeds(pump_status);
            }
            else
                LOG_WARN("Pump is already off\n");

		    coap_set_status_code(response, CHANGED_2_04);
	    }

        //  PUMP_PURE
        else if((strncmp(action, getPumpStatus(PUMP_PURE), len) == 0)){
            if(pump_status != PUMP_PURE){
                pump_status = PUMP_PURE;
                setPumpLeds(pump_status);
            }
            else
                LOG_WARN("Pump is already in pure mode\n");
        }

        // PUMP_ACID
        else if((strncmp(action, getPumpStatus(PUMP_ACID), len) == 0)){
            if(pump_status != PUMP_ACID){
                pump_status = PUMP_ACID;
                setPumpLeds(pump_status);
            }
            else
                LOG_WARN("Pump is already in acid mode\n");
        }

        // PUMP_BASE
        else if((strncmp(action, getPumpStatus(PUMP_BASE), len) == 0)){
            if(pump_status != PUMP_BASE){
                pump_status = PUMP_BASE;
                setPumpLeds(pump_status);
            }
            else
                LOG_WARN("Pump is already in base mode\n");
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