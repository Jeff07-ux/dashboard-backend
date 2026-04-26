import urllib.request
import urllib.error
import urllib.parse
import sys

url = 'http://localhost:8000/api/upload'
file_path = 'C:/Users/pc/Desktop/fichier.xlsx'

with open(file_path, 'rb') as f:
    file_content = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
data = []
data.append(b'--' + boundary.encode('utf-8'))
data.append(b'Content-Disposition: form-data; name="file"; filename="fichier.xlsx"')
data.append(b'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
data.append(b'')
data.append(file_content)
data.append(b'--' + boundary.encode('utf-8') + b'--')
data.append(b'')

body = b'\r\n'.join(data)

req = urllib.request.Request(url, data=body)
req.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary)

try:
    with urllib.request.urlopen(req) as response:
        print('Status:', response.status)
        print('Body:', response.read().decode('utf-8')[:500])
except urllib.error.HTTPError as e:
    print('HTTP Error Status:', e.code)
    print('HTTP Error Body:', e.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)
