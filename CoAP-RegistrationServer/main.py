from CoAPServer import CoAPServer
from resources.CoAPConfig import CoAPConfig

def main():
    '''
    Main function
    :return: None
    '''
    
    server = CoAPServer(CoAPConfig.host, CoAPConfig.port)
    
    try:
        print("CoAP server start")
        server.listen(10)
        
    except KeyboardInterrupt:
        print("\nServer Shutdown")
        server.close()
        print("Exiting...")

if __name__ == "__main__":
    main()