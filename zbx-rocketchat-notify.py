#!/usr/bin/env python3

import datetime
import sys
import requests
import tempfile
import base64

if len(sys.argv) < 3:
    sys.exit(1)

webhook_url = sys.argv[1]
zbx_subject = sys.argv[2]
zbx_message = sys.argv[3]

# constants

zabbix_url = sys.argv[4]
zabbix_user = sys.argv[5]
zabbix_password = sys.argv[6]

period = 3600
stime = (datetime.datetime.now() - datetime.timedelta(seconds=period)).strftime("%Y%m%d%H%M%S")
drawtype = 2
width = 350
height = 100

colors = {
    'Disaster': '#E45959',
    'High': '#F6505C',
    'Average': '#FF9962',
    'Warning': '#FFC859',
    'Information': '#5C9DFA'
}
unclassified_color = '#97AAB3'

# {HOST.NAME1}#{EVENT.NAME}#{TRIGGER.STATUS}#{TRIGGER.SEVERITY}#{EVENT.ID}#{ITEM.VALUE1}#{ITEM.NAME1}#{ITEM.ID1}

event_data = zbx_message.split("#")

event_hostname = event_data[0]
event_name = event_data[1]
event_status = event_data[2]
event_severity = event_data[3]
event_id = event_data[4]
event_item_value = event_data[5]
event_item_name = event_data[6]
event_item_id = event_data[7]
event_trigger_url = event_data[8]

try:
    color_by_severity = colors[event_severity]
except Exception:
    color_by_severity = unclassified_color

color = "#00FF00" if "OK:" in zbx_subject else color_by_severity

# Get Graph image

session = requests.Session()

response = session.post(zabbix_url, {
     'name': zabbix_user,
     'password': zabbix_password,
     'autologin': 1,
     'enter': 'SignIn'
}, verify=False)

image_graph = ""

if response.status_code == 200:
    graph_url = zabbix_url + "/chart3.php"

    graph_response = session.get(graph_url, params={'name': event_item_name,
                                                     'period': period,
                                                     'stime': stime,
                                                     'width': width,
                                                     'height': height,
                                                     'items[0][itemid]': event_item_id,
                                                     'items[0][drawtype]': drawtype,
                                                     'items[0][color]': '00FF00'}, stream=True, verify=False)

    if graph_response.status_code == 200 and graph_response.headers['Content-Type'] == 'image/png':
        buffer = tempfile.SpooledTemporaryFile(max_size=1e9)
        for chunk in graph_response.iter_content(1024):
            buffer.write(chunk)
        buffer.seek(0)

        graph_data = base64.b64encode(buffer.read()).decode('ascii')

        image_graph = "data:image/png;base64," + graph_data


chat_message = {
    "username": "Zabbix",
    "icon_url": "https://assets.zabbix.com/img/newsletter/2016/icons/share-logo-z.png",
    "text": zbx_subject,
    "attachments": [{
      "title": event_name + " on " + event_hostname,
      "title_link": event_trigger_url,
      "color": color,
      "fields": [{
         "title": "Status",
         "value": event_status,
         "short": True
      }, {
         "title": "Severity",
         "value": event_severity,
         "short": True
      }, {
          "title": "Last value",
          "value": event_item_value,
          "short": True
      }, {
          "title": "Host",
          "value": event_hostname,
          "short": True
      }, {
          "title": "Event ID",
          "value": event_id,
          "short": True
      }],
      "image_url": image_graph
    }]
}

r = requests.post(webhook_url, json=chat_message)

try:
    if r.status_code == 200 and r.json()['success']:
        sys.exit(0)
    else:
        sys.exit(2)
except Exception:
    sys.exit(3)


