import sys
import serial
import time
import os
from datetime import datetime
import json

CMD_LINEBREAK = b'\r\n'

PORT = "/dev/ttyUSB2"
BAUD = 115200

# Mosquitto.org Settings
MQTT_URL="f10310uj1y9sw0000.m2.exosite.io"
CERTS_FOLDER = 'certs'
CA_NAME = 'murano-ca.crt'
CERT_NAME = "murano.crt"
KEY_NAME = "murano.key"

def send(data):
    with serial.Serial(PORT, BAUD, xonxoff=False,
            rtscts=True, dsrdtr=True, timeout=12) as ser:
        ser.write(data)

def send_and_watch(cmd, timeout=10, success=None, failure=None, echo_cmd=None):
    with serial.Serial(PORT, BAUD, xonxoff=True,
            rtscts=True, dsrdtr=True, timeout=timeout) as ser:

        ser.write(cmd.encode('utf-8') + CMD_LINEBREAK)

        t_start = time.time()
        reply = list()
        while True:
            if ser.in_waiting:
                line = ser.readline()
                echo = False
                if echo_cmd:
                    echo = line.decode('utf-8').strip().startswith(echo_cmd)
                if line != CMD_LINEBREAK and not echo:
                    line = line.decode('utf-8').strip()
                    reply.append('\t' + line)
                    if success and line.startswith(success):
                        return ("Success", reply, time.time()-t_start)
                    if failure and line.startswith(failure):
                        return ("Error", reply, time.time()-t_start)
            if (time.time()-t_start) > timeout:
                return ("Timeout", reply, time.time()-t_start)
            time.sleep(0.02)

def AT(cmd="", timeout=5, success="OK", failure="+CME ERROR"):
    cmd = 'AT' + cmd
    print("----------- ", cmd, " -----------")
    reply = send_and_watch(cmd, echo_cmd=cmd, timeout=timeout, success=success, failure=failure)
    print("{0} ({1:.2f}secs):".format(reply[0], reply[2]))
    print(*reply[1], sep='\n')
    print('')
    return reply

# Restart board
if "--reboot" in sys.argv:
    AT('+CFUN=1,1', timeout=30, success="*PSUTTZ")

# AT('+CMNB=3') # Set preference for nb-iot (doesn't work with nb-iot)
AT() # Check modem is responding
AT("+CMEE=2") # Set debug level
# Hardware Info
AT("+CPIN?") # Check sim card is present and active
AT("+CGMM") # Check module name
AT("+CGMR") # Firmware version
AT('+GSN') # Get IMEI number
AT('+CCLK?') # Get system time
# Signal info
AT("+COPS?") # Check opertaor info
AT("+CSQ") # Get signal strength
AT('+CPSI?') # Get more detailed signal info
AT('+CBAND?') # Get band
# GPRS info
AT("+CGREG?") # Get network registration status
AT("+CGACT?") # Show PDP context state
AT('+CGPADDR') # Show PDP address
cgcontrdp = AT("+CGCONTRDP") # Get APN and IP address
# Check nb-iot Status
AT('+CGNAPN')

APN = cgcontrdp[1][0].split(",")[2]
IP = cgcontrdp[1][0].split(",")[3]

############################### PING/NTP ##################################

# Ping - works :-)
if sys.argv[1] == "ping":
    print("++++++++++++++++++++ PING +++++++++++++++++++++\n")
    cstt = AT('+CSTT?')
    if APN not in cstt[1][0]:
        AT('+CSTT="{}"'.format(APN))
        AT('+CIICR')
    AT('+CIFSR', success=IP)
    AT('+CIPPING="www.google.com.au"')

# Get NTP time - working :-)
if sys.argv[1] == "ntp":
    print("++++++++++++++++++++ NTP +++++++++++++++++++++\n")
    AT('+SAPBR=3,1,"APN","{}"'.format(APN))
    AT('+SAPBR=1,1')
    AT('+SAPBR=2,1')
    AT('+CNTP="pool.ntp.org",0,1,1')
    AT('+CNTP', timeout=3, success="+CNTP")
    AT('+SAPBR=0,1')

############################### MQTT ######################################

# MQTT (No SSL) - Working :-)
if sys.argv[1] == "mqtt-nossl":
    print("++++++++++++++++++++ MQTT - NO SSL +++++++++++++++++++++\n")
    AT("+CNACT=1") # Open wireless connection
    AT("+CNACT?") # Check connection open and have IP
    AT('+SMCONF="CLIENTID",1233')
    AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    AT('+SMCONF="CLEANSS",1')
    AT('+SMCONF="URL","{}","1883"'.format(MQTT_URL)) # Set MQTT address
    smstate = AT('+SMSTATE?') # Check MQTT connection state
    if smstate[1][0].split(":")[1].strip() == "0":
        AT('+SMCONN', timeout=30) # Connect to MQTT
    msg = "Hello Moto {}".format(datetime.now())
    AT('+SMPUB="test001","{}",1,1'.format(len(msg)), timeout=30, success=">") # Publish command
    send_and_watch(msg)
    #AT('+SMSUB="test1234",1')
    AT('+SMDISC') # Disconnect MQTT
    AT("+CNACT=0") # Close wireless connection

############################### SSL/TLS ##################################

# Check certs on device - working :-)
if sys.argv[1] == "certs-check":
    print("++++++++++++++++++++ CERTS - CHECK +++++++++++++++++++++\n")
    AT('+CFSINIT')
    cfsgfis = AT('+CFSGFIS=3,"{}"'.format(CA_NAME))
    file_size = cfsgfis[1][0].split(" ")[1]
    AT('+CFSRFILE=3,"{}", 0, {}, 0'.format(CA_NAME, file_size), timeout=30)
    AT('+CFSTERM')

    AT('+CFSINIT')
    cfsgfis = AT('+CFSGFIS=3,"{}"'.format(CERT_NAME))
    file_size = cfsgfis[1][0].split(" ")[1]
    AT('+CFSRFILE=3,"{}", 0, {}, 0'.format(CERT_NAME, file_size), timeout=30)
    AT('+CFSTERM')

    AT('+CFSINIT')
    cfsgfis = AT('+CFSGFIS=3,"{}"'.format(KEY_NAME))
    file_size = cfsgfis[1][0].split(" ")[1]
    AT('+CFSRFILE=3,"{}"", 0, {}, 0'.format(KEY_NAME, file_size), timeout=30)
    AT('+CFSTERM')

# Delete certs on device - working :-)
if sys.argv[1] == "certs-delete":
    print("++++++++++++++++++++ CERTS - DELETE +++++++++++++++++++++\n")
    AT('+CFSINIT')
    AT('+CFSDFILE=3,"{}"'.format(CA_NAME))
    AT('+CFSTERM')
    AT('+CFSINIT')
    AT('+CFSDFILE=3,"{}"'.format(CERT_NAME))
    AT('+CFSTERM')
    AT('+CFSINIT')
    AT('+CFSDFILE=3,"{}"'.format(KEY_NAME))
    AT('+CFSTERM')

# Load a cert from a file on computer - working :-)
if sys.argv[1] == "certs-load":
    print("++++++++++++++++++++ CERTS - LOAD +++++++++++++++++++++\n")
    AT('+CFSTERM')
    AT('+CFSINIT')
    with open(os.path.join(CERTS_FOLDER, CA_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},10000'.format(CA_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(5)
        AT('+CFSTERM')
    AT('+CFSINIT')
    with open(os.path.join(CERTS_FOLDER, CERT_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},10000'.format(CERT_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(5)
        AT('+CFSTERM')
    AT('+CFSINIT')
    with open(os.path.join(CERTS_FOLDER, KEY_NAME),'rb') as f:
        data = f.read()
        AT('+CFSWFILE=3,"{}",0,{},10000'.format(KEY_NAME, len(data)), success="DOWNLOAD")
        send(data)
        time.sleep(5)
        AT('+CFSTERM')

# MQTT (SSL) - No client cert, working for Mosquitto.org :-(
if sys.argv[1] == "mqtt-cacert":
    print("++++++++++++++++++++ MQTT - CA Cert Only +++++++++++++++++++++\n")
    AT('+CNACT=1, "{}"'.format(APN)) # Open wireless connection
    AT('+CNACT?') # Check connection open and have IP

    # +CSSLCFG SSL Configurations
    AT('+CSSLCFG="sslversion",  0, 3')            # QAPI_NET_SSL_PROTOCOL_TLS_1_2
    AT('+CSSLCFG="ciphersuite", 0, 0, 0xC02A')    # QAPI_NET_TLS_ECDH_RSA_WITH_AES_256_CBC_SHA384
    AT('+CSSLCFG="ciphersuite", 0, 1, 0xC02B')    # QAPI_NET_TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
    AT('+CSSLCFG="ciphersuite", 0, 2, 0xC02C')    # QAPI_NET_TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
    AT('+CSSLCFG="ciphersuite", 0, 3, 0xC02D')    # QAPI_NET_TLS_ECDH_ECDSA_WITH_AES_128_GCM_SHA256
    AT('+CSSLCFG="ciphersuite", 0, 4, 0xC02E')    # QAPI_NET_TLS_ECDH_ECDSA_WITH_AES_256_GCM_SHA384
    AT('+CSSLCFG="ciphersuite", 0, 5, 0xC02F')    # QAPI_NET_TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
    AT('+CSSLCFG="ciphersuite", 0, 6, 0xC031')    # QAPI_NET_TLS_ECDH_RSA_WITH_AES_128_GCM_SHA256
    AT('+CSSLCFG="protocol",    0, 1')            # QAPI_NET_SSL_TLS_E
    AT('+CSSLCFG="sni",         0, "{}"'.format(MQTT_URL))
                                                  # SNI
    AT('+CSSLCFG="ctxindex", 0')                  # Use index 1
    AT('+CSSLCFG="convert", 2, "{}"'.format(CA_NAME))
    time.sleep(2)
    AT('+CSSLCFG="convert", 1, "{}", "{}"'.format(CERT_NAME, KEY_NAME))
    time.sleep(2)

    # +SMCONF Set MQTT Parameters
    AT('+SMCONF="KEEPTIME",60') # Set the MQTT connection time (timeout?)
    AT('+SMCONF="CLEANSS",1')
    AT('+SMCONF="URL","{}","443"'.format(MQTT_URL)) # Set MQTT address

    # +SMSSL Select SSL Configurations
    AT('+SMSSL=1, "{}", "{}"'.format(CA_NAME, CERT_NAME))
    AT('+SMSSL?')
    AT('+SMSTATE?') # Check MQTT connection state

    AT('+SMCONN', timeout=60, success="OK") # Connect to MQTT
    AT('+SMSTATE?', timeout=5)              # Check MQTT connection state

    msg = json.dumps({
        "user_id" : "Austin",
        "timestamp" : str(datetime.now())
    })
    AT('+SMPUB="$resource/data_in","{}",1,1'.format(len(msg))) # Publish command
    send(msg.encode('utf-8'))

    #AT('+SMSUB="test1234",1')
    AT('+SMDISC')  # Connect to MQTT
    AT("+CNACT=0") # Close wireless connection

