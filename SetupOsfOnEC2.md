# OSF evaluation on AWS EC2

## Quick Start Guide

For setting up this project on your local environment, follow these steps:

### 1. Change to Project Directory

Setup for git:
```bash
git config --global user.name 'Your github account name' 
git config --global user.email 'Your email address'        
git config --global core.editor 'code --wait'
git config --global merge.tool 'code --wait "$MERGED"'
git config --global push.default simple
git config --list  # githuconfig confirmation 
```

You need generate and register your github token in your gitconfig.

link: https://docs.github.com/ja/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

Navigate to the project root directory:
```bash
cd aws-xray-evaluation
git clone https://github.com/RCOSDP/RDM-osf.io.git
git clone https://github.com/RCOSDP/RDM-ember-osf-web.git
git clone https://github.com/RCOSDP/RDM-modular-file-renderer.git
git clone https://github.com/RCOSDP/RDM-waterbutler.git
```


### 2. Docker Build
setup docker and docker compose.

link: https://docs.docker.jp/v1.12/compose/install.html

link: https://docs.docker.com/engine/install/ubuntu/

Build Docker images for each module:
```bash
sudo docker build RDM-ember-osf-web -t rdm-osf-web:dev
sudo docker build RDM-modular-file-renderer -t rdm-mfr:dev
sudo docker build RDM-waterbutler -t rdm-wb:dev
sudo docker build fakecas -t rdm-fakecas:dev
sudo docker build RDM-osf.io -t rdm-osf:dev
```

### 3. Setup Loopback Interface


Configure your loopback interface on your machine:
```bash
sudo apt install net-tools
sudo ifconfig lo:0 192.168.168.167 netmask 255.255.255.255 up
```

### 4. Change to Module Directory

Navigate to the module directory:
```bash
cd aws-xray-evaluation/RDM-osf.io/
```

### 5. Copy and Update Local Settings

Copy the local settings of the project:
```bash
cp ./website/settings/local-dist.py ./website/settings/local.py
cp ./api/base/settings/local-dist.py ./api/base/settings/local.py
cp ./admin/base/settings/local-dist.py ./admin/base/settings/local.py
cp ./tasks/local-dist.py ./tasks/local.py
```

Update the local settings of the project:
RDM-osf.io/.docker-compose.env
```bash

DOMAIN=http://ec2.compute-1.amazonaws.com:5000/
INTERNAL_DOMAIN=http://web:5000/
API_DOMAIN=http://ec2.compute-1.amazonaws.com:8000/
ELASTIC_URI=elasticsearch:9200
ELASTIC6_URI=elasticsearch6:9201
OSF_DB_HOST=postgres
DB_HOST=mongo
WATERBUTLER_URL=http://ec2.compute-1.amazonaws.com:7777
WATERBUTLER_INTERNAL_URL=http://wb:7777
CAS_SERVER_URL=http://ec2.compute-1.amazonaws.com:8080
MFR_SERVER_URL=http://ec2.compute-1.amazonaws.com:7778
BROKER_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://192.168.168.167:6379/1
ADMIN_URL=http://ec2.compute-1.amazonaws.com:8001/
ADMIN_INTERNAL_DOCKER_URL=http://admin:8001/
ALLOWED_HOSTS=ec2.compute-1.amazonaws.com,localhost

```
RDM-osf.io/.docker-compose.osf-web.env
```bash
OSF_COOKIE_DOMAIN=ec2.compute-1.amazonaws.com
OSF_URL=http://ec2.compute-1.amazonaws.com:5000/
OSF_API_URL=http://ec2.compute-1.amazonaws.com:8000
OSF_MFR_URL=http://ec2.compute-1.amazonaws.com:7778/
OSF_RENDER_URL=http://ec2.compute-1.amazonaws.com:7778/render
OSF_FILE_URL=http://ec2.compute-1.amazonaws.com:7777
OSF_HELP_URL=http://ec2.compute-1.amazonaws.com:5000/help
OSF_COOKIE_LOGIN_URL=http://ec2.compute-1.amazonaws.com:8080/login
OSF_OAUTH_URL=http://ec2.compute-1.amazonaws.com:8080/oauth2/profile
SHARE_BASE_URL=https://share.osf.io/
SHARE_API_URL=https://share.osf.io/api/v2
SHARE_SEARCH_URL=https://share.osf.io/api/v2/search/creativeworks/_search
CAS_URL=http://ec2.compute-1.amazonaws.com:8080

```

RDM-osf.io/.docker-compose.wb.env

```bash
DEBUG=
SERVER_CONFIG_DEBUG=
SERVER_CONFIG_HMAC_SECRET=changeme
SERVER_CONFIG_ADDRESS=0.0.0.0
SERVER_CONFIG_DOMAIN=http://ec2.compute-1.amazonaws.com:7777
OSF_AUTH_CONFIG_API_URL=http://ec2.compute-1.amazonaws.com:5000/api/v1/files/auth/
OSF_URL=http://ec2.compute-1.amazonaws.com:5000

TASKS_CONFIG_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
```

RDM-osf.io/admin/base/settings/local.py
```bash
SESSION_COOKIE_DOMAIN = 'ec2.compute-1.amazonaws.com'
from .defaults import *

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,osf.io').split(',')

```

RDM-osf.io/docker-compose.override.yml

```bash
version: "3.4"

services:
  mfr_requirements:
    image: rdm-mfr:dev
  mfr:
    image: rdm-mfr:dev
  wb_requirements:
    image: rdm-wb:dev
  wb:
    image: rdm-wb:dev
  wb_worker:
    image: rdm-wb:dev
  ember_osf_web:
    image: rdm-osf-web:dev
    environment:
      - BACKEND=env
    env_file:
      - .docker-compose.osf-web.env
    volumes:
      - ../RDM-ember-osf-web:/code:cached
      - ember_osf_web_dist_vol:/code/dist
  requirements:
    image: rdm-osf:dev
  assets:
    image: rdm-osf:dev
  admin_assets:
    image: rdm-osf:dev
  worker:
    image: rdm-osf:dev
  admin:
    image: rdm-osf:dev
  api:
    image: rdm-osf:dev
  web:
    image: rdm-osf:dev
  preprints:
    environment:
      - BACKEND=env
    env_file:
      - .docker-compose.osf-web.env
  fakecas:
    image: quay.io/centerforopenscience/fakecas:master
    command: fakecas -host=0.0.0.0:8080 -osfhost=ec2.compute-1.amazonaws.com:5000 -dbaddress=postgres://postgres@postgres:5432/osf?sslmode=disable
  registries:
    environment:
      - BACKEND=env
    env_file:
      - .docker-compose.osf-web.env
  reviews:
    environment:
      - BACKEND=env
    env_file:
      - .docker-compose.osf-web.env
```

RDM-osf.io/website/settings/local.py
```bash
DOMAIN = PROTOCOL + 'ec2.compute-1.amazonaws.com:5000/'
INTERNAL_DOMAIN = DOMAIN
API_DOMAIN = PROTOCOL + 'ec2.compute-1.amazonaws.com:8000/'
OSF_COOKIE_DOMAIN = 'ec2.compute-1.amazonaws.com'

```


### 6. Docker Compose Up Requirements

Ensure you have the required services running:
```bash
sudo docker-compose up requirements wb_requirements mfr_requirements
```

### 7. Start Core Component Services (Detached)

Spin up denpent services:
```bash
sudo docker-compose up -d elasticsearch elasticsearch6 postgres mongo rabbitmq
```

### 8. Assets Setup

Remove your existing node_modules and start the assets:
```bash
sudo rm -Rf ./node_modules
sudo rm -Rf ./website/static/vendor/bower_components
sudo rm -Rf ./admin/node_modules
sudo rm -Rf ./admin/static/vendor/bower_components
sudo docker-compose up -d assets admin_assets
```

### 9. More Services

Upgrade dependency
RDM-osf.io/requirements/dev.txt
```bash
pytest-xdist==1.34.0
```

Start additional services:
```bash
sudo docker-compose up -d unoconv mfr wb fakecas sharejs
```

### 10. Database Migration
When starting with an empty database you will need to run migrations and populate preprint providers. 
Perform database migrations:
```bash
sudo docker-compose run --rm web python3 manage.py migrate
```
See the [Running arbitrary commands](RDM-osf.io/README-docker-compose.md#running-arbitrary-commands) section below for instructions.

### 11. Run the Project

Finally start the OSF Web, API Server, and Preprints (Detached):
```bash
sudo docker-compose up -d wb_worker worker web api admin preprints ember_osf_web registries reviews
```

We can see containers and images list.
```bash
sudo docker iamges
sudo docker ps
```


We can see the rdm page through browser. 

link : https://EC2-url:5000/

![top page](/images/rdmTop.png)


Once you follow these steps, you should have a local environment up and running for development.

## Configuration Guide

### 1. Let's Encrypt Setup
**Configure AWS Credentials**

Use the AWS CLI Docker image to configure your AWS credentials:

```bash
sudo docker run --rm -it -v "/root/.aws:/root/.aws" amazon/aws-cli configure
```
**Verify AWS Credentials**
Nii has a Certificate Management Service link: https://certs.nii.ac.jp/ . You can contact to them if your service is created on NII infrastructure.

Verify if your AWS credentials are working and have nominal access to Route 53:

```
sudo docker run --rm -it -v "/root/.aws:/root/.aws" amazon/aws-cli route53 list-hosted-zones
```
**Request a Let's Encrypt Wildcard Certificate**

Use the certbot/dns-route53 Docker image to request a wildcard certificate, forwarding your AWS credentials:

```
certbot certonly --dns-route53 --domain "your.com" --domain "*.your.com"
```

**Automate Certificate Renewal**

Create systemd timer to automate certificate renewal, then daemon-reload, enable, and start the timer.
Create /etc/systemd/system/certbot.service. For the docker command, remove --it for non-interactive execution by systemd, and pass /usr/bin to the container to allow execution of systemctl by --deploy-hook:
```
[Unit]
Description=Let's Encrypt certificate renewal

[Service]
Type=oneshot
ExecStart=certbot renew --dns-route53 --quiet --agree-tos --deploy-hook "cd /home/ubuntu/aws-xray-evaluation/RDM-osf.io && sudo docker-compose restart web admin wb fakecas ember_osf_web  preprints registries reviews"
```

Then create /etc/systemd/system/certbot.timer:
```
[Unit]
Description=Monthly renewal of Let's Encrypt certificates

[Timer]
OnCalendar=monthly
RandomizedDelaySec=12 hours
Persistent=true

[Install]
WantedBy=timers.target
```

### 2. User Management

**Setup SMTP**rdm

We need to setup smtp and mailutils. We can install postfix with local only and deefault hostname
```bash
apt install postfix mailutils
```

/etc/postfix/main.cf
```bash

mynetworks = 10.0.0.0/0 # your network 
inet_interfaces = all # 
```

Test for sending mail
```bash
echo "test" | mail -s test root@ip-1-1-1-1.ap-northeast-1.compute.internal
```

```bash
root@ip-1-1-1-1:/etc/postfix# mail
"/var/mail/root": 1 message 1 new
>N   1 root               Mon Mar  4 05:29  14/656   test
? 1  ### input number
From: root <root@ip-1-1-1-1.ap-northeast-1.compute.internal>
test
```


**Create User**

Method 1:
Create a user via register link: https://EC2-url:5000/register/

Method 2:
Create a user directly through the RDM shell.
```bash
docker-compose run --rm web invoke shell
```
Create an OSF User with python code:
```python
user = OSFUser.create(username=<your_user@cos.io>,password=<password>,fullname=<full name>)
```
> **Note:** User's registration status is to be shifted to True by adding `user.is_registered = True` `user.have_email = True` and `user.date_confirmed = timezone.now()`. Due to the lack of an inherited mail server in local environment, the newly created account is unable to send confirmation emails making the account unconfirmed.

Save your user with `user.save()`
Commit the changes with `commit()`

**Admin User**

Please refer to [RDM-osf.io/admin/README.md](RDM-osf.io/admin/README.md) for instructions on how to make existing user super admin.
