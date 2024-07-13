#include "contiki.h"
#include "coap-engine.h"
#include "coap-blocking-api.h"
#include "net/ipv6/uip.h"
#include "net/ipv6/uip-ds6.h"
#include "sys/etimer.h"
#include "sys/process.h"
#include "os/dev/leds.h"
#include <stdio.h>


/* ---------------------------------------------- */
/*               Log configuration                */
/* ---------------------------------------------- */

#include "sys/log.h"
#define LOG_MODULE "Actuator fans"
#define LOG_LEVEL LOG_LEVEL_INFO


/* ---------------------------------------------- */
/*               CoAP configuration               */
/* ---------------------------------------------- */

// Macros
#define SERVER_EP "coap://[fd00::1]:5683"
#define NODE_NAME_JSON "{\"name\":\"actuator_fans\",\"status\":\"off\"}"
#define MAX_REGISTRATION_RETRY 5

// Variables
static coap_endpoint_t server_ep;
static coap_message_t request[1];
static char *service_registration_url = "/registration";
static int max_registration_retry = MAX_REGISTRATION_RETRY;

// Handler to check if the registration was successful
void client_chunk_handler(coap_message_t *response){

	// Timeout
	if(response == NULL) {
		LOG_ERR("Request timed out\n");
	}
	
	// Error
	else if(response->code != 65 && response->code != 68){
		LOG_ERR("Error: %d\n",response->code);	
	}
	
	// Success
	else{
		LOG_INFO("Registration successful\n");
		max_registration_retry = 0;
		return;
	}
	
	// Registration failed, retry at most max_registration_retry times
	max_registration_retry--;
	if(max_registration_retry==0)
		max_registration_retry=-1;
}

// Declare resource defined in resources/resource_fans.c
extern coap_resource_t res_fans;


/* ---------------------------------------------- */
/*              Thread configuration              */
/* ---------------------------------------------- */

// Timer
static struct etimer sleep_timer;

// Process declaration
PROCESS(actuator_fans, "Actuator fans");
AUTOSTART_PROCESSES(&actuator_fans);

/*
* This process is used to register the actuator to the server
* and to activate the resource "fans"
* 
* The actuator try to register MAX_REGISTRATION_RETRY times
* if it fails, it will go to sleep for 30 seconds and then try again
*/
PROCESS_THREAD(actuator_fans, ev, data){

    PROCESS_BEGIN();


	/* -------------- Registration --------------- */

	// Registration is tried until is successful
	while(max_registration_retry!=0){
		
		// Prepare registration request
		coap_endpoint_parse(SERVER_EP, strlen(SERVER_EP), &server_ep);
		coap_init_message(request, COAP_TYPE_CON,COAP_POST, 0);
		coap_set_header_uri_path(request, service_registration_url);
		coap_set_payload(request, (uint8_t *)NODE_NAME_JSON, sizeof(NODE_NAME_JSON) - 1);
	
		// Send registration request
		COAP_BLOCKING_REQUEST(&server_ep, request, client_chunk_handler);
    
		// Registration failed
        if(max_registration_retry == -1) {
			etimer_set(&sleep_timer, 30 * CLOCK_SECOND);
			PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&sleep_timer));
			max_registration_retry = MAX_REGISTRATION_RETRY;
		}
	}
    

	/* ----------- Resource activation ----------- */
    coap_activate_resource(&res_fans, "fans");


    PROCESS_YIELD();

    PROCESS_END();
}