#! /bin/bash
ssh -i ~/awskeys/joshdea-iad-uk.pem -t ec2-user@54.173.207.11 'dev/stop.sh'
scp -i ~/awskeys/joshdea-iad-uk.pem app.py ec2-user@54.173.207.11:~/dev/app.py
scp -i ~/awskeys/joshdea-iad-uk.pem templates/index.html ec2-user@54.173.207.11:~/dev/templates/index.html