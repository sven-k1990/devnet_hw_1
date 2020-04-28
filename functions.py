from datetime import datetime
from netmiko import ConnectHandler
import os
from getpass import getpass
import sys
import csv

def get_conf_name(hostname):
    return "{}-{}.txt".format(hostname, get_date())


def get_date():
    return datetime.strftime(datetime.now(), '%d%m%Y-%H%M')


def make_dir(hostname, path=None):
    if path is None:
        path = os.path.join(os.getcwd(), 'config_backups', hostname)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path
    else:
        if not os.path.isdir(path):
            os.makedirs(path)
            print("not in {}".format(path))
        return path


def save_config(hostname, data, path=None):
    save_file = os.path.join(make_dir(hostname, path),
                             get_conf_name(hostname))

    if not os.path.exists(save_file):
        write_to_disk(save_file, data)
    else:
        save_file = "{}-1.cfg".format(save_file.split('.')[0])
        write_to_disk(save_file, data)


def write_to_disk(file_path, data):
    with open(file_path, 'w') as f:
        f.write(data)


def make_connection(device):
    if not device['port']:
        device['port'] = '22'
    try:
        connection = ConnectHandler(host=device['ip'],
                                    username=device['username'],
                                    port = device['port'],
                                    password =device['password'],
                                    device_type=device['device_type'],
                                    secret=device['secret']
                                    )
        return connection
    except Exception as E:
        print(E)


def close_connection(connection):
#Disconnect from device
    connection.disconnect()


def send_command(connection, command):
    try:
        if not (connection is None):
            connection.enable()
            return connection.send_command(command)
        else:
            print('Have not connect')
    except Exception as E:
        print(E)


def get_config(connection):
    return send_command(connection, 'show running-config')


def check_type(connection):
    if send_command(connection, 'show_version').find("PE") == -1:
        return 'NPE'
    else:
        return 'PE'


def check_ntp(config):
    if config.find('ntp') == -1:
        return 'NTP is OFF'
    else:
        return 'NTP is ON'


def check_cdp(config):
    if config.find('cdp enable') == -1:
        return 'CDP is ON'
    else:
        return 'CDP is OFF'


def config_ntp(connection, ntp):
    if send_command(connection, 'ping {}'.format(ntp)):
        commands = [ 'ntp server {}'.format(ntp),]
        set_config(connection, commands)
    else:
        print("Can't configure ntp")


def check_ntp_status(connection):
    if send_command(connection, 'show ntp status').find('Clock is synchronized') == -1:
        return 'NTP not sync'
    else:
        return 'NTP sync'


def set_config(connection, commands):
    for command in commands:
        connection.config_mode()
        send_command(connection, command)
        connection.exit_config_mode()


def configure_tz(connection, tz):
    commands = ['clock timezone {}'.format(tz), 'exit']
    set_config(connection, tz)


##Принимаю данные от пользователя для исключения повторений в хостах применяю структуру множество
def get_data_from_user():
    print('Пожалуйста введите доменные имена или ip-адреса через запятую пример 192.168.100.1,192.168.100.2')
    ip_range = input("Eсли используется нестандартный порт введите его через двоеточие 192.168.100.1:2222, 192.168.100.2:9999 : ")
    username = input('Введите имя пользователя: ')
    password = getpass("Введите пароль: ")
    secret = getpass("Введите секрет(Если он схож с паролем нажмите продолжить): ")
    if len(secret) <= 1:
        secret = password
    ntp = input('Введите ip ntp сервера: ')
    tz = input('Введите временную зону в формате GMT 0 0: ')
    if len(tz) <= 1:
        tz = 'GMT 0 0'
    return (set(ip_range.split(',')),
            username,
            password,
            secret,
            ntp,
            tz)


## Получаю данные из csv файла
def get_data_from_csv(file):
    device_list = list()
    with open(file,'r') as f:
        devices = csv.DictReader(f)
        for row in devices:
            device_list.append(row)
        return {'hosts': device_list,
                'ntp': '132.163.96.5',
                'tz': 'GMT 0 0',}

##Нормальзует данные полученные от пользователя в интерактивном режиме
def normalized_data():
    data = get_data_from_user()
    hosts = list()
    for ip in data[0]:
        if len(ip.split(':')) == 2:
            ip_ = ip.split(':')[0]
            port = ip.split(':')[1]
        else:
            ip = ip
            port = '22'
        row = {'ip': ip_,
               'port': port,
               'username': data[1],
               'password': data[2],
               'device_type': 'cisco_ios',
               'secret': data[3],
               }
        hosts.append(row)
    return {'hosts'
            : hosts,
            'ntp': data[4],
            'tz': data[5]}

##Обработка show version возвращает кортеж
def get_version(data):
    return data.split('\n')[0].split(',')[-1].strip().split(' ')[-1], \
           data.split('\n')[1].split(',')[1].strip().split(' ')[-1].replace('(', '').replace(')', '')


def start_process(device, config_data):
    print("-"*10)
    print("Working with {}".format(device['ip']))
    conn = make_connection(device)
    config = get_config(conn)
    save_config(device['ip'], config)
    configure_tz(conn, config_data['tz'])
    config_ntp(conn, config_data['ntp'])
    cdp = check_cdp(config)
    type_ = check_type(conn)
    ntp = check_ntp(config)
    version = get_version(send_command(conn, 'show version'))
    string = "{}|{}|{}|{}|{}|{}".format(device['ip'],
                                        version[0],
                                        version[1],
                                        type_,
                                        cdp,
                                        ntp)
    print(string)
    conn.disconnect()




