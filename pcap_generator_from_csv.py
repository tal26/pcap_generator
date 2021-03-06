#!/usr/bin/python

import sys
import binascii
import random
import argparse

#for timestamping
import time
import re

# ----- ===== Configurable parameteres ==== ----
# DO NOT TOUCH OTHER VARIABLES
# default necessary values if there is nothing provided
# default_src_mac = "00:00:00:00:00:01"
# default_dst_mac = "00:00:00:00:00:02"
# default_src_ip = "10.0.0.1"
# default_dst_ip = "192.168.88.8"
# default_src_port = 1234
# default_dst_port = 808
# default_vlan = None
# default_ttl = 64

#DEFINE HERE THE DIFFERENT PACKETS SIZE YOU WANT - ALL HEADER INFORMATION WILL BE THE SAME FOR ALL PACKET SIZES
#This needs to be list object: if you want to use one packet size must be a list with two elements, where the latter is
#empty, i.e., packet_size=(64,)
# packet_sizes = (64,) #,  # PCAP file will be generated for these
                # 128,  # packet sizes - we always generate all packets with these packet sizes
                # 256,
                # 512,
                # 1024,
                # 1280,
                # 1500)

# COLORIZING
none = '\033[0m'
bold = '\033[01m'
disable = '\033[02m'
underline = '\033[04m'
reverse = '\033[07m'
strikethrough = '\033[09m'
invisible = '\033[08m'

black = '\033[30m'
red = '\033[31m'
green = '\033[32m'
orange = '\033[33m'
blue = '\033[34m'
purple = '\033[35m'
cyan = '\033[36m'
lightgrey = '\033[37m'
darkgrey = '\033[90m'
lightred = '\033[91m'
lightgreen = '\033[92m'
yellow = '\033[93m'
lightblue = '\033[94m'
pink = '\033[95m'
lightcyan = '\033[96m'
CBLINK = '\33[5m'
CBLINK2 = '\33[6m'
# ------ =================================== -----



# Global header for pcap 2.4
pcap_global_header = ('D4 C3 B2 A1'
                      '02 00'  # File format major revision (i.e. pcap <2>.4)
                      '04 00'  # File format minor revision (i.e. pcap 2.<4>)
                      '00 00 00 00'
                      '00 00 00 00'
                      'FF FF 00 00'
                      '01 00 00 00')

# pcap packet header that must preface every packet
pcap_packet_header = ('T1 T1 T1 T1'  # time in seconds (little endian)
                      'T2 T2 T2 T2'  # time in microseconds (little endian)
                      'XX XX XX XX'  # Frame Size (little endian)
                      'YY YY YY YY')  # Frame Size (little endian)

eth_header = ('00 E0 4C 00 00 01'  # Dest Mac
              '00 04 0B 00 00 02'  # Src Mac
              '08 00')  # Protocol (0x0800 = IP)

ip_header = ('45'  # IP version and header length (multiples of 4 bytes) (4+4 bits)
             '00'  #DSCP + ECN (6 + 2 bits)
             'XX XX'  # Length (16 bits) - will be calculated and replaced later
             '00 00' # Identification (16 bits)
             '40 00' # Flags + frag_Offset (3 + 13 bits)
             'TT 11'  # TTL + Protocol (11-UDP) (8 + 8 bits)
             'YY YY'  # Checksum - will be calculated and replaced later (16 bits)
             'SS SS SS SS'  # Source IP (Default: 10.1.0.1) (32 bits)
             'DD DD DD DD')  # Dest IP (Default: 10.0.0.1) (32 bits)

udp_header = ('ZZ ZZ'  # Source port - will be replaced lated
              'XX XX'  # Destination Port - will be replaced later
              'YY YY'  # Length - will be calculated and replaced later
              '00 00')

gtp_header = ('30'              # Version(3), Proto type(1) and other zero fields
              'FF'              # Type: T-PDU
              'LL LL'           # Length - will be calculated later
              'TE ID TE ID')    # TEID - will be added later


def _reverseEndian(hexstring):
    #create a list of 2-characters of the input
    big_endian = re.findall('..', hexstring)
    little_endian=""
    for i in reversed(big_endian):
        little_endian+=i

    return little_endian


def createTimestamp(**kwargs):
    # this is a timestamp in seconds.microseconds, e.g., 1570435931.7557144
    _time = kwargs.get('time',time.time())
    #check for float type
    if isinstance(_time,float):
        _time="%.8f" % _time # str(time) is not working well below python3 as floats become reduced to two decimals only
    #split it to seconds and microseconds
    _time=_time.split('.')
    # time is a list now
    sec  = _time[0]
    usec = _time[1]
    # convert the to hex
    sec = ("%08x" % int(sec))   # now, we have sec in hex (big endian)
    usec = ("%08x" % int(usec)) # now, we have usec in hex (big endian)

    sec  = _reverseEndian(sec)
    usec = _reverseEndian(usec)
    return (sec,usec)

def getByteLength(str1):
    return int(len(''.join(str1.split())) / 2)


# # raw_input returns the empty string for "enter"
# yes = {'yes','y', 'ye', ''}
# no = {'no','n'}
#
# def confirm(**args):
#     '''
#     This function asks for confirmation? To specify the question, **args are defined
#     :param args: with_something=with something, do=do, e.g.,  Do you really want to overwrite test.pcap
#     :return:
#     '''
#     print "Do you really want to "+ args.get('do',"do something") + args.get('with_something') + '? (yes/no,y/n) [Default: Yes]'
#     choice = raw_input().lower()
#     print choice
#     if choice in yes:
#         return True
#     elif choice in no:
#         return False
#     else:
#         print("Please respond with 'yes/y' or 'no/n'")
#         exit(-1)

first_byte_to_write = True

def writeByteStringToFile(bytestring, filename):
    bytelist = bytestring.split()
    bytes = binascii.a2b_hex(''.join(bytelist))
    bitout = open(filename, 'ab')
    bitout.write(bytes)


def backspace(n):
    # print((b'\x08' * n).decode(), end='') # use \x08 char to go back
    sys.stdout.write('\r' * n)  # use '\r' to go back


def calculateRemainingPercentage(current, n):
    percent = str("all-byte packets: %d%%\n" % (int((current / float(n)) * 100)))
    sys.stdout.write(percent)

#    backspace(len(percent))  # back for n chars


def readFile(input):
    headers = list() # list of dictionaries
    with open(input, 'r') as lines:
        line_num = 1
        for line in lines:
            #remove blank spaces
            line = line.strip()
            #removed blank lines
            if line:
                #omit commented lines
                packet_counter=1
                if not (line.startswith("#", 0, 1)):
                    #assume that the desctiption file is a CSV file and look like this:
                    ##timestamp=123123124.123123, src_mac=<SRC_MAC>,dst_mac=<DST_MAC>, src_ip=<SRC_IP>, dst_ip<DST_IP>, src_port=<SRC_PORT>,dst_port=<DST_PORT>,gtp=<GTP_TEID>, ?? - unimplemented
                    #let us further assume that order is not important
                    one_line = line.split(',')
                    # this dictionary will store eventually one complete header
                    header = {
                            'timestamp':"",
                            'src_mac':"",
                            'dst_mac':"",
                            'src_ip':"",
                            'dst_ip':"",
                            'src_port':"",
                            'dst_port':"",
                            'gtp':"",
                            'ext_src_ip':"",
                            'ext_dst_ip':"",
                            'vlan':"",
                            'ttl':""
                            # TODO: add more header fields here
                    }
                    for i in one_line:
                        #remove white spaces
                        i=i.strip()
                        #check whether there is a remaining comma at the end (strip above already makes it a zero-length
                        #white space, so we only need to check that

                        if i != "":
                            #OK, everything is prepared, let's start to parse the relevant data
                            header_row=i.split('=')
                            #now, we only will have key=value pairs, let's see whether they are meaningful
                            #note we need to iterate the whole line first, as it should not be ordered.
                            for h in header.keys():
                                if header_row[0] == h:
                                    if h.endswith("mac"):
                                        header[h] = parseMAC(header_row[1])
                                    elif h.endswith('ip'):
                                        header[h] = parseIP(header_row[1])
                                    elif h.endswith('timestamp'):
                                        header[h] = header_row[1] #it is a string, but it can remain a string
                                    else: #all other header fields that are represented as INTEGER
                                    #e.g., ***port,***vlan, ***gtp, ***ttl
                                        header[h] = int(header_row[1])
                                    # TODO: handle here futher header fields that are different from the above
                                    # or update the above ones to parse the new header fields accordingly
                    headers.append(header)

    #Set necessary header fields (e.g., source MAC) data to default values if csv file did contain them
    for h in headers:
        #inside the list
        for hh in h:
            #inside one header
            if hh == 'timestamp' and h[hh]=="":
                h[hh] = default_timestamp

            if hh == 'src_mac' and h[hh]=="":
                h[hh]=parseMAC(default_src_mac)

            if hh == 'dst_mac' and h[hh]=="":
                h[hh] = parseMAC(default_dst_mac)

            if hh == 'src_ip' and h[hh] =="":
                h[hh]=parseIP(default_src_ip)

            if hh == 'dst_ip' and h[hh] == "":
                h[hh] = parseIP(default_dst_ip)

            if hh == 'src_port' and h[hh] == "":
                h[hh] = default_src_port

            if hh == 'dst_port' and h[hh] == "":
                h[hh] = default_dst_port

            if hh == 'vlan' and h[hh] == "":
                h[hh] = default_vlan

            if hh == 'gtp' and h[hh] == "":
                h[hh] = None
            if hh == "ttl" and h[hh] == "":
                h[hh] = default_ttl

    return headers


def generateTraceFromFile(inputfile, pcapfile, **kwargs):
    '''
    This function will read the input file and creates a pcap from its content
    :param inputfile: input file to read
    :param pcapfile: pcap output file
    :param kwargs:
        packet_sizes = list of packetsizes required
        src_mac = default src_mac
        dst_mac = default dst_mac
        src_ip = default src_ip
        dst_ip = default dst_ip
        ttl = default_ttl
        src_port = default src_port
        dst_port = default dst_port
        vlan = default vlan
        gtp_teid = default gtp_teid
        timestamp = default timestamp

    :return: None
    '''
    global default_src_mac, default_dst_mac
    global default_src_ip, default_dst_ip
    global default_src_port, default_dst_port
    global default_vlan
    global default_ttl
    global packet_sizes
    global verbose
    global default_timestamp

    packet_sizes = []
    default_src_mac = kwargs.get('src_mac')
    default_dst_mac = kwargs.get('dst_mac')
    default_src_ip = kwargs.get('src_ip')
    default_dst_ip = kwargs.get('dst_ip')
    default_src_port = int(kwargs.get('src_port')) #CONVERT TO INT
    default_dst_port = int(kwargs.get('dst_port')) #CONVERT TO INT
    default_vlan = kwargs.get('vlan') #IS NOT CONVERTED TO INT as default is None
    gtp_teid = kwargs.get('gtp_teid') #IS NOT CONVERTED TO INT as default is None
    verbose = kwargs.get('verbose')
    default_timestamp = kwargs.get('timestamp')
    default_ttl = int(kwargs.get('ttl')) #CONVERT TO INT

    if default_vlan is not None:
        default_vlan = int(default_vlan)

    ps = kwargs.get('packet_sizes')
    for i in ps:
        packet_sizes.append(int(i))

    headers=readFile(inputfile)
    n=len(headers)

    # write out header information to file - 5-tuples will be printed in an .nfo files as well
    for i in range(1, int(n) + 1):
        # print out the remaining percentage to know when the generate will finish
        calculateRemainingPercentage(i, int(n))

        # set here the header variables
        timestamp = headers[i-1]['timestamp']
        sport = headers[i-1]['src_port']
        dport = headers[i-1]['dst_port']
        src_ip = headers[i-1]['src_ip']
        dst_ip = headers[i-1]['dst_ip']
        src_mac = headers[i-1]['src_mac']
        dst_mac = headers[i-1]['dst_mac']
        vlan = headers[i-1]['vlan']
        ttl = headers[i-1]['ttl']

        gtp_teid = headers[i-1]['gtp']
        ext_src_ip = headers[i-1]['ext_src_ip']
        ext_dst_ip = headers[i-1]['ext_dst_ip']

        #VLAN HANDLING - it requires other eth_type and additional headers
        if vlan is None:
            # update ethernet header for each packet
            eth_header = dst_mac + ' ' + src_mac + "0800"
        else:
            eth_header = dst_mac + ' ' + src_mac + \
                         '81 00' + \
                         '0V VV' + \
                         '08 00'
            # update vlan header
            eth_header = eth_header.replace('0V VV', "0%03x" % vlan)

        # GTP tunneling: it requires additional headers
        if gtp_teid is not None:
            gtp = gtp_header
            gtp = gtp.replace('TE ID TE ID', "%08x" % gtp_teid)

            # generate the external headers
            gtp_dport = 2152
            gtp_sport = 2152
            ext_udp = udp_header.replace('XX XX', "%04x" % gtp_dport)
            ext_udp = ext_udp.replace('ZZ ZZ', "%04x" % gtp_sport)
            ext_ip = ip_header
            ext_ip = ext_ip.replace('SS SS SS SS', ext_src_ip)
            ext_ip = ext_ip.replace('DD DD DD DD', ext_dst_ip)
            ext_ip = ext_ip.replace('TT',"%02x" % ttl)

        # update ip header - see on top how it looks like (the last bytes are encoding the IP address)
        ip = ip_header
        #update source IP
        ip = ip.replace('SS SS SS SS', src_ip)
        #update destination IP
        ip = ip.replace('DD DD DD DD', dst_ip)
        #update ttl
        ip = ip.replace('TT', "%02x" % ttl)
        # print (ip)

        # update ports
        udp = udp_header.replace('XX XX', "%04x" % dport)
        udp = udp.replace('ZZ ZZ', "%04x" % sport)

        # create packets with the different packet sizes but with the same 5-tuple
        for pktSize in packet_sizes:
            # generate the packet payload (random)
            message = getMessage(pktSize)

            # generate the headers (in case of tunneling: internal headers)
            udp_len = getByteLength(message) + getByteLength(udp_header)
            udp = udp.replace('YY YY', "%04x" % udp_len)

            ip_len = udp_len + getByteLength(ip)
            # print(ip_len)
            ip = ip.replace('XX XX', "%04x" % ip_len)
            # print(ip)
            checksum = ip_checksum(ip.replace('YY YY', '00 00'))
            ip = ip.replace('YY YY', "%04x" % checksum)
            tot_len = ip_len

            # encapsulation (external header)
            if gtp_teid is not None:
                gtp_len = ip_len
                gtp = gtp.replace('LL LL', "%04x" % gtp_len)

                # generate the external headers
                ext_udp_len = gtp_len + getByteLength(gtp) + getByteLength(udp_header)
                ext_udp = ext_udp.replace('YY YY', "%04x" % ext_udp_len)

                ext_ip_len = ext_udp_len + getByteLength(ip_header)
                if ext_ip_len > 1500:
                    print("WARNING! Generating >MTU size packets: {}".format(ext_ip_len))
                ext_ip = ext_ip.replace('XX XX', "%04x" % ext_ip_len)
                checksum = ip_checksum(ext_ip.replace('YY YY', '00 00'))
                ext_ip = ext_ip.replace('YY YY', "%04x" % checksum)

                tot_len = ext_ip_len

            pcap_len = tot_len + getByteLength(eth_header)
            hex_str = "%08x" % pcap_len
            reverse_hex_str = hex_str[6:] + hex_str[4:6] + hex_str[2:4] + hex_str[:2]

            pcaph = pcap_packet_header.replace('XX XX XX XX', reverse_hex_str)
            pcaph = pcaph.replace('YY YY YY YY', reverse_hex_str)

            #adding timestamp
            if timestamp is None: #timestamp was not set, use current time
              time = createTimestamp()
            else:
              time = createTimestamp(time=timestamp)
            pcaph = pcaph.replace('T1 T1 T1 T1', time[0]) # time[0] is seonds
            pcaph = pcaph.replace('T2 T2 T2 T2', time[1]) # time[1] is useonds

            # at the first packet we need the global pcap header
            if i == 1:
                if gtp_teid is not None:
                    bytestring = pcap_global_header + pcaph + eth_header + ext_ip + ext_udp + gtp + ip + udp + message
                else:
                    bytestring = pcap_global_header + pcaph + eth_header + ip + udp + message
            # for the rest, only the packets are coming, i.e., no pcap_global_header is needed
            else:
                if gtp_teid is not None:
                    bytestring = pcaph + eth_header + ext_ip + ext_udp + gtp + ip + udp + message
                else:
                    bytestring = pcaph + eth_header + ip + udp + message

            # this function is writing out pcap file per se
            if verbose:
                print("Packet to be written out:\n{}".format(headers[i-1]))

            writeByteStringToFile(bytestring, pcapfile + str(".%dbytes.pcap" % pktSize))

            # we have to change back the variable fields to their original fixed value else they will not be found
            ip = ip.replace("%04x" % ip_len, 'XX XX')
            udp = udp.replace("%04x" % udp_len, 'YY YY')
            if gtp_teid is not None:
                gtp = gtp.replace("%04x" % gtp_len, 'LL LL')
                ext_udp = ext_udp.replace("%04x" % ext_udp_len, 'YY YY')
                ext_ip = ext_ip.replace("%04x" % ext_ip_len, 'XX XX')

def getRandomMAC():
    return "1a" + str("%0.10X" % random.randint(1,0xffffffffff))

def getRandomIP():
    # to avoid multicast addresses (range is between 0.0.0.0/8 and 223.255.255.255)
    ip = str("%0.8X" % random.randint(0x01000000,0xdfffffff))

    #avoid others 127.0.0.0/8 - hex(127)=7F
    while ip.startswith("7F"):
        #print "Ooops, accidentally a 127.0.0.0/8 IP was generated...REGENERATING!"
        ip = str("%0.8X" % random.randint(0x01000000, 0xdfffffff))

    return ip

def getRandomPort(**args):
    '''
    Use 'exlude=[XXX]' to exlude a list of ports (even 1 port has to be defined as a list)
    '''
    port = random.randint(1,65535)
    exlude = args.get("exclude", [4305])
    if(port in exlude):
        getRandomPort()
    return int(port)

def parseMAC(mac):
    ret_val=mac.replace(":","").upper()
    if len(ret_val) != 12: #check mac address length
        print("ERROR during parsing mac address - not long enough!: {}".format(mac))
        exit(-1)
    return  ret_val

def parseIP(ip):
    ret_val = ""
    #split IP address into 4 8-bit values
    ip_segments=ip.split(".")
    for i in ip_segments:
        ret_val+=str("%0.2X" % int(i))
    if len(ret_val) != 8: #check length of IP
        print("ERROR during parsing IP address - not long enough!: {}".format(ip))
        exit(-1)
    return ret_val

def splitN(str1, n):
    return [str1[start:start + n] for start in range(0, len(str1), n)]


# Calculates and returns the IP checksum based on the given IP Header
def ip_checksum(iph):
    # print(iph)
    # split into bytes
    words = splitN(''.join(iph.split()), 4)

    csum = 0
    for word in words:
        csum += int(word, base=16)

    csum += (csum >> 16)
    csum = csum & 0xFFFF ^ 0xFFFF

    return csum

def getMessage(packetsize):
    message = ''
    for i in range(0, int(packetsize) - 46):  # 46 = eth + ip + udp header
        message += "%0.2X " % random.randint(0, 255)

    return message


def showHelp():
    print("{}usage: pcap_generator_from_csv.py <input_csv_file> <desired_output_pcapfile_prefix>{}".format(bold,none))
    print('Example: ./pcap_generator_from_csv.py input.csv output')
    print("{}Note: Existing files with the given <desired_output_pcapfile_prefix>.[PacketSize].pcap will be overwritten!{}".format(yellow,none))

    print("This python script generates pcap files according to the header information stored in a CSV file")
    print("See 'input.csv' file for CSV details")
    print("")
    print("Supported header fields: {}\n" \
                                               "  VLAN \n" \
                                               "  L2 (src and dst MAC) \n" \
                                               "  L3 (src and dst IP, TTL) \n" \
                                               "  L4 (src and dst PORT) \n" \
                                               "  GTP_TEID\n " \
                                               "  TIMESTAMP for each packet\n ".format(bold,none))
    print("Any further header definition in the file is sleemlessly ignored!")
    print("")
    print("In case of missing L2, L3, L4 information in the inputfile, default values will be used!")
    print("To change the default values, modify the source code (first couple of lines after imports)")
    print("")
    print("Default packet size is 64-byte! It is defined as a list in the source code! " \
          "Extend it if necessary!\n")
    exit(0)


"""------------------------------------------"""
""" End of functions, execution starts here: """
"""------------------------------------------"""
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Usage of PCAP generator from CSV file")
    parser.add_argument('-i','--input',nargs=1,
                        help="Specify the name of the input CSV file. "
                             "For syntax, see input.csv.example!",
                        required=True)
    parser.add_argument('-o','--output',nargs=1,
                        help="Specify the output PCAP file's basename! "
                             "Output will be [output].[PACKETSIZE]bytes.pcap extension is not needed!",
                        required=True)
    parser.add_argument('-p','--packetsizes',nargs=1,
                        help="Specify here the required packetsize! "
                        "In case of more than one, just create a comma separated list "
                        "such as 64,112,42. Default: 64",
                        required=False,
                        default=['64'])
    parser.add_argument('-a','--src_mac',nargs=1,
                        help="Specify default source MAC address if it is not present "
                        "in the input.csv. Default: 00:00:00:00:00:01",
                        required=False,
                        default=["00:00:00:00:00:01"])
    parser.add_argument('-b', '--dst_mac', nargs=1,
                        help="Specify default destination MAC address if it is not present "
                             "in the input.csv. Default: 00:00:00:00:00:02",
                        required=False,
                        default=["00:00:00:00:00:02"])
    parser.add_argument('-c', '--vlan', nargs=1,
                        help="Specify default VLAN tag if it is not present "
                             "in the input.csv. Default: No VLAN",
                        required=False,
                        default=[None])
    parser.add_argument('-d', '--src_ip', nargs=1,
                        help="Specify default source IP address if it is not present "
                             "in the input.csv. Default: 10.0.0.1",
                        required=False,
                        default=["10.0.0.1"])

    parser.add_argument('-e', '--dst_ip', nargs=1,
                        help="Specify default destination IP address if it is not present "
                             "in the input.csv. Default: 10.0.0.2",
                        required=False,
                        default=["10.0.0.2"])

    parser.add_argument('-f', '--ttl', nargs=1,
                        help="Specify default TTL if it is not present "
                             "in the input.csv. Default: 10",
                        required=False,
                        default=["10"])

    parser.add_argument('-g', '--src_port', nargs=1,
                        help="Specify default source port if it is not present "
                             "in the input.csv. Default: 1234",
                        required=False,
                        default=["1234"])
    parser.add_argument('-j', '--dst_port', nargs=1,
                        help="Specify default destination port if it is not present "
                             "in the input.csv. Default: 80",
                        required=False,
                        default=["80"])
    parser.add_argument('-k', '--gtp_teid', nargs=1,
                        help="Specify default GTP_TEID if it is not present "
                             "in the input.csv. Default: NO GTP TEID",
                        default=[None])
    parser.add_argument('-l', '--timestamp', nargs=1,
                        help="Specify the default timestamp for each packet if it is not present "
                             "in the input.csv. Default: Use current time",
                        required=False,
                        default=[None])

    parser.add_argument('-v','--verbose', action='store_true', required=False, dest='verbose',
    help="Enabling verbose mode")
    parser.set_defaults(verbose=False)

    args = parser.parse_args()

    input = args.input[0]
    output = args.output[0]
    packet_sizes = (args.packetsizes[0]).split(',')
    src_mac = args.src_mac[0]
    dst_mac = args.dst_mac[0]
    src_ip = args.src_ip[0]
    dst_ip = args.dst_ip[0]
    src_port = args.src_port[0]
    dst_port = args.dst_port[0]
    vlan = args.vlan[0]
    gtp_teid = args.gtp_teid[0]
    timestamp = args.timestamp[0]
    ttl = args.ttl[0]

    verbose=args.verbose

    print("{}The following arguments were set:{}".format(bold,none))
    print("{}Input file:            {}{}{}".format(bold,green,input,none))
    print("{}Output file:           {}{}{}".format(bold,green,output,none))
    print("{}Packetsizes:           {}{}{}".format(bold,green,packet_sizes,none))
    print("{}SRC MAC if undefined:  {}{}{}".format(bold,green,src_mac,none))
    print("{}DST MAC if undefined:  {}{}{}".format(bold,green,dst_mac,none))
    print("{}SRC IP if undefined:   {}{}{}".format(bold,green,src_ip,none))
    print("{}DST IP if undefined:   {}{}{}".format(bold,green,dst_ip,none))
    print("{}TTL if undefined:      {}{}{}".format(bold,green,ttl,none))
    print("{}SRC PORT if undefined: {}{}{}".format(bold,green,src_port,none))
    print("{}DST PORT if undefined: {}{}{}".format(bold,green,dst_port,none))
    print("{}VLAN if undefined:     {}{}{}".format(bold,green,vlan,none))
    print("{}GTP_TEID if undefined  {}{}{}".format(bold,green,gtp_teid,none))
    print("{}TIMESTAMP if undefined:{}{}{}".format(bold,green,timestamp,none))



    for i in packet_sizes:
        open(str("{}.{}bytes.pcap".format(output,i)),'w') # delete contents




    generateTraceFromFile(
                            input,
                            output,
                            packet_sizes=packet_sizes,
                            src_mac=src_mac,
                            dst_mac=dst_mac,
                            src_ip=src_ip,
                            dst_ip=dst_ip,
                            src_port=src_port,
                            dst_port=dst_port,
                            vlan=vlan,
                            verbose=verbose,
                            gtp_teid=gtp_teid,
                            timestamp=timestamp,
                            ttl=ttl
                         )
