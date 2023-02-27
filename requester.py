import argparse
from datetime import datetime
from enum import Enum
import socket
import struct 

class Packet_Type(Enum):
    REQUEST = 'R'
    DATA = 'D'
    END = 'E'

def parse_command_line_args():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-p', '--requester_port', help='port on which the requester waits for packets', required=True, type=int)
    parser.add_argument('-o', '--file_name', help='the name of the file that is being requested', required=True)

    args = parser.parse_args()
    return args

# printing information for each packet that arrives
def print_receipt_information(header, data, sender_address):
    packet_type = header[0].decode('ascii')
    if (packet_type == 'D'):
        print('DATA Packet')
    elif (packet_type == 'E'):
        print('END Packet')

    sender_address = str(sender_address[0]) + ':' + str(sender_address[1])

    print('recv time:        ', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    print('sender addr:      ', sender_address)
    print('sequence num:     ', header[1])
    print('length:           ', header[2])
    print('payload:          ', data.decode("utf-8"))
    print()

def print_summary(sender_address, total_data_packets, total_data_bytes, start_time, end_time):
    time_elapsed = end_time - start_time
    time_elapsed_in_miliseconds = time_elapsed.total_seconds() * 1000.0
    rate = total_data_packets / time_elapsed.total_seconds()
    sender_address = str(sender_address[0]) + ':' + str(sender_address[1])
    print('Summary')
    print('sender addr:              ', sender_address)
    print('Total Data packets:       ', total_data_packets)
    print('Total Data bytes:         ', total_data_bytes)
    print('Average packets/ second:  ', rate)
    print('Duration of the test:     ', time_elapsed_in_miliseconds, ' ms')

# reads and parses tracker.txt into a nested dictionary
# details of nested dictionary are outlined below
def read_and_parse_tracker_file(file_name):
    try:
        file = open(file_name, "r")
    except:
        print('Please enter the correct file name!')
        return
    
    file_lines = file.readlines()

    # below is the structure of the nested dictionary
    # filename: {
    #          id: {
    #              sender_host_name: "some_host_name",
    #              sender_port_number: 12345
    #          }
    # }
    tracker_dict =  {}

    for file_line in file_lines:
        words_in_line = file_line.split()
        curr_file_name = words_in_line[0]
        id = int(words_in_line[1])
        sender_host_name = words_in_line[2]
        sender_port_number = words_in_line[3]

        if curr_file_name not in tracker_dict:
            tracker_dict[curr_file_name] = {}
        if id not in tracker_dict[curr_file_name]:
            tracker_dict[curr_file_name][id] = {}

        tracker_dict[curr_file_name][id]['sender_host_name'] = sender_host_name
        tracker_dict[curr_file_name][id]['sender_port_number'] = int(sender_port_number)

    return tracker_dict

# send request packed with file name to the sender
def send_request_packet_to_sender(tracker_dict, file_name, id):
    data = file_name.encode()
    file_id_dict = tracker_dict[file_name]
    
    sender_host_name = file_id_dict[id]['sender_host_name']
    sender_port_number = file_id_dict[id]['sender_port_number']

    # assemble udp header
    packet_type = (Packet_Type.REQUEST.value).encode('ascii')
    sequence_number = 0
    data_length = 0
    header = struct.pack('!cII', packet_type, sequence_number, data_length)

    packet_with_header = header + data

    sock.sendto(packet_with_header, (sender_host_name, sender_port_number))

# for testing
# requester_port = 12345
# file name: 'tracker-test.txt'

# set global variables from command line args
args = parse_command_line_args()
requester_port = args.requester_port
requested_file_name = args.file_name
tracker_dict = read_and_parse_tracker_file('tracker-test.txt') #TODO: change this to tracker.txt

# create socket object
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
requester_host_name = socket.gethostname()
sock.bind((requester_host_name, requester_port))

# request the senders for packets
if requested_file_name not in tracker_dict:
    print('error: no information on requested file')
    print('exiting program...')
    exit()

file_id_dict = tracker_dict[requested_file_name]
number_of_chunks_to_request = len(file_id_dict)
start_time = datetime.now()

for id in range(0, number_of_chunks_to_request):
    send_request_packet_to_sender(tracker_dict, requested_file_name, id + 1)

# wait for requested packets from sender while the END packet has not been sent

# TODO: change this file name when ready
results_file = open('result.txt', 'a')

end_packets_received = 0
data_packets_received = 0
data_bytes_received = 0

while end_packets_received != number_of_chunks_to_request:
    packet_with_header, sender_address = sock.recvfrom(1024)
    header = struct.unpack("!cII", packet_with_header[:9])
    data = packet_with_header[9:]

    packet_type = header[0].decode('ascii')

    if (packet_type == 'D'):
        results_file.write(data.decode("utf-8"))
        data_packets_received += 1
        payload_length = header[2]
        data_bytes_received += payload_length
    print_receipt_information(header, data, sender_address)

    if (packet_type == 'E'):
        end_packets_received += 1
        end_time = datetime.now()
        print_summary(sender_address, data_packets_received, data_bytes_received, start_time, end_time)
        
        # reset statistics
        start_time = datetime.now()
        data_packets_received = 0
        data_bytes_received = 0
    
results_file.close()


