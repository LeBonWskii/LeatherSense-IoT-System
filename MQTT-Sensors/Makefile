CONTIKI_PROJECT = MQTT-Sensors
all: $(CONTIKI_PROJECT)

MODULES_REL += ../cJSON-master

CONTIKI = ../../..

MODULES += $(CONTIKI_NG_APP_LAYER_DIR)/mqtt
MODULES += cJSON

LDLIBS += -lm

-include $(CONTIKI)/Makefile.identify-target

MODULES_REL += arch/platform/$(TARGET)


SRCS := $(filter-out ../cJSON-master/test.c, $(SRCS))


include $(CONTIKI)/Makefile.include