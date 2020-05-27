import http.client, json

url = "vaquita.auth.eu-central-1.amazoncognito.com"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "Basic aSdxd892iujendek328uedj"
    }

params = {
    "grant_type": "authorization_code",
    "client_id": "ca3psh04mecinnt32lebhbme4",
    "code": "58c945df-0c48-4f0b-a61e-39b5abd81904",
    "redirect_uri": "https://5kcl2f8eb1.execute-api.eu-central-1.amazonaws.com/prod/vaquita/web"
}

conn = http.client.HTTPSConnection(url)
conn.request("POST", "/oauth2/token", json.dumps(params), headers)
r1 = conn.getresponse()

# response = conn.getresponse()
# print(response.read().decode())

print(r1.status, r1.reason)
data1 = r1.read()
print (data1)