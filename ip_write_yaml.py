import yaml

# 설정할 데이터 구조
data = {
    'server': {
        'host': '192.168.0.17',
        'ssh_key': 'server.key'
    },
    'RPi3B+': {
        'host': '192.168.0.14',
        'ssh_key': 'rpi3b_plus.key'
    },
    'RPi4B': {
        'host': '192.168.0.15',
        'ssh_key': 'rpi4b.key'
    },
    'RPi5': {
        'host': '192.168.0.19',
        'ssh_key': 'rpi5.key'
    }
}

# YAML 파일 쓰기
with open('config.yaml', 'w') as file:
    yaml.dump(data, file, default_flow_style=False)