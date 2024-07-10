from CoAPServer import CoAPServer
from resources.config import host, port

def main():
    '''
    Main function
    :return: None
    '''
    
    server = CoAPServer(host, port)
    
    try:
        print("CoAP server start")
        server.listen(10)
        
    except KeyboardInterrupt:
        print("Server Shutdown")
        server.close()
        print("Exiting...")

if __name__ == "__main__":
    main()