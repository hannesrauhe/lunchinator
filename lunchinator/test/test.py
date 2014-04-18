from lunch_server import lunch_server
import thread

if __name__ == "__main__":
    s = lunch_server()
    thread.start_new_thread(s.start_server, ())
    
    inp = ""
    while(inp != "stop"):
        inp = raw_input("> ")
        if inp == "stop":
            s.call("HELO_STOP test", ["127.0.0.1"])
