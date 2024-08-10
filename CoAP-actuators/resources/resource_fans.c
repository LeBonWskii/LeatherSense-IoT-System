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
#define LOG_MODULE "Fans - resource"
#define LOG_LEVEL LOG_LEVEL_INFO


/* ---------------------------------------------- */
/*              Status configuration              */
/* ---------------------------------------------- */

// Fans status enumeration
typedef enum {
    FANS_OFF = 0,
    FANS_EXHAUST = 1,
    FANS_COOLING = 2,
    FANS_BOTH = 3
} fans_status_t;

// String representation of the fans status
const char* getFansStatus(fans_status_t status){
    switch(status){
        case FANS_OFF:
            return "off";
        case FANS_EXHAUST:
            return "exhaust";
        case FANS_COOLING:
            return "cooling";
        case FANS_BOTH:
            return "both";
        default:
            return "unknown";
    }
}

// Initial status
static fans_status_t fans_status = FANS_OFF;


/* ---------------------------------------------- */
/*             Resource configuration             */
/* ---------------------------------------------- */

// Handler declaration for PUT request
static void res_put_handler(coap_message_t *request, coap_message_t *response, uint8_t *buffer, uint16_t preferred_size, int32_t *offset);

// Resource definition
RESOURCE(res_fans,
         "title=\"LEATHERSENSE: ?actuator_fans=<string>\" POST/PUTaction=<action>\";rt=\"Control\";if=\"actuator\"",
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

    // Check the action and set the fans status accordingly
    if(action!=NULL && strlen(action)!=0){

        // FANS_OFF -> GREEN led
        if((strncmp(action, getFansStatus(FANS_OFF), len) == 0)){
            if(fans_status != FANS_OFF){
                fans_status = FANS_OFF;
                leds_off(LEDS_RED);
                leds_off(LEDS_BLUE);
                leds_on(LEDS_GREEN);
                LOG_INFO("Fans are off\n");
            }
            else
                LOG_WARN("Fans is already off\n");

		    coap_set_status_code(response, CHANGED_2_04);
	    }

        //  FANS_EXHAUST -> RED led
        else if((strncmp(action, getFansStatus(FANS_EXHAUST), len) == 0)){
            if(fans_status != FANS_EXHAUST){
                fans_status = FANS_EXHAUST;
                leds_off(LEDS_BLUE);
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                LOG_INFO("Fans are in exhaust mode\n");
            }
            else
                LOG_WARN("Exhaust mode already on\n");
            
            coap_set_status_code(response, CHANGED_2_04);
        }

        // FANS_COOLING -> BLUE led
        else if((strncmp(action, getFansStatus(FANS_COOLING), len) == 0)){
            if(fans_status != FANS_COOLING){
                fans_status = FANS_COOLING;
                leds_off(LEDS_GREEN);
                leds_off(LEDS_RED);
                leds_on(LEDS_BLUE);
                LOG_INFO("Fans are in cooling mode\n");
            }
            else
                LOG_WARN("Cooling mode already on\n");
            
            coap_set_status_code(response, CHANGED_2_04);
        }

        // FANS_BOTH -> RED + BLUE leds (PURPLE)
        else if((strncmp(action, getFansStatus(FANS_BOTH), len) == 0)){
            if(fans_status != FANS_BOTH){
                fans_status = FANS_BOTH;
                leds_off(LEDS_GREEN);
                leds_on(LEDS_RED);
                leds_on(LEDS_BLUE);
                LOG_INFO("Fans are in both exhaust and cooling modes\n");
            }
            else
                LOG_WARN("Both modes already on\n");
            
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