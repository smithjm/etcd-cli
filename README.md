etcd-cli is a CLI for Etcd, however the input is completely defined using a YAML schema and the output is defined using a Jinja template. This means adding an additional directory in Etcd you don't need to change the source code.

This is Alpha level software at this point...

# Install required packages

```bash
pip -r requirements.txt
```
Would seem the package *etcd* is broken just clone it and run *python setup.py install*.

There are examples schema/template in resp. folders.

# TODO

- Add options list, modify, delete
- Add validation using Cerberus (http://cerberus.readthedocs.org/en/latest/)
- Clean up YAML input schemas
- Add input without positional argument
- Parse template as YAML after JINJA
- Add JINJA templating to YAML input

# Examples

**Example adding host:**

```bash
$ ./etcd-cli.py -d add host foo.example.com --ip 10.130.197.17 \
--netmask 255.255.255.0 --gw 10.130.197.254 --hwaddr 6c:ae:8b:60:46:ba \
--site eur-1
[INFO    ] Using config file: /home/user/.etcd-cli.conf
[INFO    ] Loading template: templates/host.jinja
[INFO    ] Set: /host/foo.example.com/site: eur-1
[INFO    ] Set: /host/foo.example.com/eth0/ip: 192.168.0.1
[INFO    ] Set: /host/foo.example.com/eth0/hwaddr: 6c:ae:8b:60:46:ba
[INFO    ] Set: /host/foo.example.com/eth0/netmask: 255.255.255.0
[INFO    ] Set: /host/foo.example.com/eth0/gw: 192.168.0.254
[INFO    ] Set: /hwaddr/3c:ae:6b:60:46:ca/interface: eth0
[INFO    ] Set: /hwaddr/3c:ae:6b:60:46:ca/hostname: foo.example.com
```

**Example adding interface:**

```bash
$ ./etcd-cli.py -d add interface eth1 --hostname foo.example.com \
--ip 10.130.197.18 --netmask 255.255.255.0 --gw 10.130.197.254 --hwaddr 3c:ae:6b:60:46:ca
[INFO    ] Using config file: /home/user/.etcd-cli.conf
[INFO    ] Loading template: templates/interface.jinja
[INFO    ] Set: /host/foo.example.com/eth1/ip: 192.168.0.1
[INFO    ] Set: /host/foo.example.com/eth1/hwaddr: 3c:5e:8b:60:46:bb
[INFO    ] Set: /host/foo.example.com/eth1/netmask: 255.255.255.0
[INFO    ] Set: /host/foo.example.com/eth1/gw: 192.168.0.254
```
