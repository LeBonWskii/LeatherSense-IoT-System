#ifndef PROJECT_CONF_H_
#define PROJECT_CONF_H_


// Set the max response payload before enable fragmentation:

#undef REST_MAX_CHUNK_SIZE
#define REST_MAX_CHUNK_SIZE    64

// Set the maximum number of CoAP concurrent transactions:

#undef COAP_MAX_OPEN_TRANSACTIONS
#define COAP_MAX_OPEN_TRANSACTIONS   6

// Set the maximum number of CoAP observe relationships:

#undef NBR_TABLE_CONF_MAX_NEIGHBORS
#define NBR_TABLE_CONF_MAX_NEIGHBORS     6

// Set the maximum number of route entries:

#undef UIP_CONF_MAX_ROUTES
#define UIP_CONF_MAX_ROUTES   4

// Set the maximum number of supported CoAP resources:

#undef UIP_CONF_BUFFER_SIZE
#define UIP_CONF_BUFFER_SIZE    240


#define LOG_LEVEL_APP LOG_LEVEL_DBG



#endif