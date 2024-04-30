from power import Monitor
import Monsoon.sampleEngine as sampleEngine
from log import WrlsEnv
import subprocess
import re
import iperf3
import logging
import time
from datetime import datetime
import socket
import paramiko
import yaml

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.debug, logging.info, logging.warning, logging.error, logging.critical
class CustomFormatter(logging.Formatter):
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def get_ip_address():
    try:
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
        return ip_addr
    except socket.error as e:
        print(f'Unable to get IP address: {e}')
        return None

def change_WiFi_interface(interf = 'wlan0', channel = 11, rate = '11M', txpower = 15):
    # change Wi-Fi interface 
    result = subprocess.run([f"iwconfig {interf} channel {channel} rate {rate} txpower {txpower}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def start_iperf3_server(server_ip, port=22):
    """서버 A에서 iperf3 서버를 비동기적으로 시작합니다."""
    # iperf3 서버 시작 (포트 5201에서 대기)
    iperf_time_interv = 2

    iperf_client = iperf3.Client()
    iperf_client.server.hostname = '192.168.0.1'
    iperf_client.port = 5201
    iperf_client.duration = 60
    iperf_client.bind_address = '192.168.0.1' # wi-fi interface's ip address

    return subprocess.Popen(['iperf3', '-s'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run_iperf3_client(client_SSH, server_ip):
    """기기 B에서 iperf3 클라이언트를 실행하여 서버 A로 데이터를 전송합니다."""
    try:
        # iperf3 클라이언트 실행 명령
        command = f'iperf3 -c {server_ip}'
        stdin, stdout, stderr = client_SSH.exec_command(command)
        
        # 실행 결과 출력
        for line in stdout.read().splitlines():
            logger.info('client_SSH:')
            logger.info(line.decode('utf-8'))
        for line in stderr.read().splitlines():
            logger.error(line.decode('utf-8'))
    except:
        logger.error("run_iperf3_client failed.")
        exit(1)

# 메인 실행
if __name__ == '__main__':
    # iperf3 서버를 시작
    server_process = start_iperf3_server()
    print("iperf3 서버가 시작되었습니다.")

    # 기기 B의 SSH 접속 정보
    host = '기기 B의 IP 주소'
    username = '기기 B의 사용자 이름'
    key_path = '기기 B의 SSH 키 경로'

    # 클라이언트 실행에 앞서 서버가 시작될 시간을 줍니다.
    time.sleep(5)
    
    # 기기 B에서 iperf3 클라이언트 실행
    run_iperf3_client(host, username, key_path)

    # 서버 프로세스 종료
    server_process.terminate()
    print("iperf3 서버가 종료되었습니다.")

# default parameters
root_path = './'
node_A_name = 'rpi3B+'
node_A_mode = "PyMonsoon"

# Set up logger
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

# Set up Power Monitor
node_A_vout = 5.0
node_A_triggerBool = True
node_A_numSamples = 5000
node_A_thld_high = 100
node_A_thld_low = 10
node_A_CSVbool = False #True
node_A_CSVname = "default"
rpi3B = Monitor.PowerMon(   node = node_A_name,
                            vout = node_A_vout,
                            mode = node_A_mode)
'''
    rpi3B.setTrigger(   bool = node_A_triggerBool,
                        numSamples = node_A_numSamples,
                        thld_high = node_A_thld_high,
                        thld_low = node_A_thld_low )
'''
rpi3B.setCSVOutput( bool = node_A_CSVbool,
                    filename = node_A_CSVname)


# Get IP address
# YAML 파일 열기 및 읽기
with open(root_path+'config.yaml', 'r') as file:
    config = yaml.safe_load(file)  # 파일에서 YAML을 읽고 파이썬 데이터 구조로 변환

# IP 주소 추출
server_ip = config['server']['host']  # 'server' 키 아래 'host' 키의 값을 추출
client_ip = config['RPi3B+']['host']

if server_ip:
    print("The IP address of the server is: ",server_ip)
else:
    print("IP address could not be determined")
    exit(1)

# Set up SSH service
client_SSH = paramiko.SSHClient()
client_SSH.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 호스트 키 자동 추가
ssh_port = 22
private_key_path = root_path + config['RPi3B+']['ssh_key']
client_id = 'pi'

try:
    mykey = paramiko.RSAKey.from_private_key_file(private_key_path)
    # SSH 연결
    client_SSH.connect(client_ip, ssh_port, client_id, pkey=mykey)
except:
    logger.error("SSH is failed.")
    exit()

# Set up iperf3
time_records = []


# Set up WiFi interface
# 1. Identify the capabilities of the Wi-Fi interface of the currently running system.
WiFi_rates = [1, 2, 5.5, 11, 6, 9, 12, 18, 24, 36, 48, 54]

# 2. Set the rate (protocl version) of the Wi-Fi interface from the low data rate.
for rate in WiFi_rates:
    # Log the start time.
    time_records.append([f'Wi-Fi start(rate: {rate})',time.time()])

    # Start power monitoring.

    
    rpi3B.startSampling()
    samples = rpi3B.getSamples()


    # Use iperf3 to measure the Wi-Fi interface's power consumption.
    iperf_result = iperf_client.run()

    if iperf_result.error:
        logging.error(iperf_result.error)
    else:
        logging.info("iperf3 is done.")

    # End power monitoring.


    # Log the end time.
    time_records.append(['Wi-Fi end(rate: , )',time.time()])

# SSH 연결 종료
client_SSH.close()

# Calculate each rate's average power consumption.
current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
filename = f"data_{current_time}.txt"
try:
    # 파일을 열려고 시도합니다.
    f = open(filename, 'w')
    f.write(time_records)
    f.close()
except OSError as e:
    # OSError 발생 시 오류 코드와 메시지를 출력합니다.
    logger.error(f"Error opening {filename}: {os.strerror(e.errno)}")


# Plot the result.




'''
# Client-Server Architecture
- Client: Raspberry Pi (conneceted to power monitor as power supplier)
- Server: Linux Desktop (conneceted to power monitor's USB interface)

# Wi-Fi interface table
'Wi-Fi AP': IPTIME AX2002-Mesh
- b, g, n, ax 20MHz, Korea
- TX power = 100
- Beacon 100ms

'AX201'
'bcm434355c0' on the RPI3+/RPI4 https://github.com/seemoo-lab/nexmon
-> ~ 802.11a/g/n/ac with up 80 MHz
data rate
- 802.11b: [1, 2, 5.5, 11] # Mbps
- 802.11g: [6, 9, 12, 18, 24, 36, 48, 54] # Mbps
- 802.11n: [
        6.5, 7.2, 13.5, 15,  
        13, 14.4, 27, 30, 19.5, 21.7, 40.5, 45,
        26, 28.9, 54, 60, 39, 43.3, 81, 90,
        52, 57.8, 108, 120, 58.5, 65, 121.5, 135, 65, 72.2, 135, 150,
        13, 14.4, 27, 30, 
        26, 28.9, 54, 60, 39, 43.3, 81, 90,
        52, 57.8, 108, 120, 78, 86.7, 162, 180,
        104, 115.6, 216, 240, 117, 130, 243, 270, 130, 144.4, 270, 300,
        19.5, 21.7, 40.5, 45,
        39, 43.3, 81, 90, 58.5, 65, 121.5, 135, 
        78, 86.7, 162, 180, 117, 130, 243, 270,
        156, 173.3, 324, 360, 175.5, 195, 364.5, 405, 195, 216.7, 405, 450,
        26, 28.8, 54, 60,
        52, 57.6, 108, 120, 78, 86.8, 162, 180,
        104, 115.6, 216, 240, 156, 173.2, 324, 360,
        208, 231.2, 432, 480, 234, 260, 486, 540, 260, 288.8, 540, 600
]

# iw https://wireless.wiki.kernel.org/en/users/documentation/iw

# SSH Key Generation
- $ ssh-keygen
- $ rpi3b_plus
- $ # just enter; empty passphase 

# iperf3
    iperf3

    -s : server mode
    -c : client mode
    -p {#}: port
    -u : use UDP rather than TCP
    -b : indicate bandwidth when using UDP
    -t {#}: time interval
    -w {#}: TCP window size (socket buffer size)
    -M {#}: set TCP maximum setment size (MTU - 40 bytes)
    -N : set TCP no delay, disabling Nagle's Algorithm
    -V : set the domain to IPv6
    -d : measure bi-direcitonal
    -n {#}: number of bytes to transmit
    -F {name}: input the data to be transmitted from a file
    -I : input the data to be transmitted from stdin
    -P #: number of parallel client thrads to run
    -T : time-to-live, for multicast (default 1)
'''