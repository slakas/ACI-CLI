#!/usr/bin/env python
# -*- encoding: utf-8 -*-
################################################################################
#     _|_|      _|_|_|  _|_|_|
#   _|    _|  _|          _|
#   _|_|_|_|  _|          _|
#   _|    _|  _|          _|
#   _|    _|    _|_|_|  _|_|_|
################################################################################
#
# Skrypt na podstawie skryptów z acitools
#
################################################################################


"""This module implements a CLI similar to Cisco IOS and NXOS
   for use with the ACI Toolkit.
"""
import sys
import cgi
import cgitb
from os import system
import getopt
import getpass
import logging
from cmd import Cmd
from engine.acitoolkit.acitoolkit import (Tenant, Contract, AppProfile, EPG, Interface, PortChannel, L2ExtDomain, Subnet,
                        PhysDomain, VmmDomain, L3ExtDomain, EPGDomain, Context, BridgeDomain, L2Interface,
                        FilterEntry, Session, Tag)
from engine.endpoints import ENDPOINTS
from engine.neigbours import NEIGHBOURS
from engine.interfaces import INTERFACE
from engine.interfaces import INTERAFES_STATS
from engine.interfaces import InterfaceCollector
# import engine.portchannel as portchannel_summary
from engine.admin_events import ShowFaults
from engine.admin_events import AuditLog
from engine.inventory import CollectInventory
import engine.debugging
import requests
from tabulate import tabulate
import yaml
import re
import pprint
READLINE = True
NOT_NO_ARGS = 'show exit help configure switchto switchback interface no'


# KONFIGURACJA LOGOWANIA DO APIC
# Produkcja
URL = 'https://sandboxapicdc.cisco.com'
LOGIN = 'admin'
PASSWORD = 'ciscopsdt'


try:
    import readline
    # The following is required for command completion on Mac OS
    import rlcompleter
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
except:
    try:
        import pyreadline
    except:
        READLINE = False


def error_message(resp):
    """
    Print an error message

    :param resp: Response object from Requests library
    :return: None
    """
    print('Error:  Unable to push configuration to APIC')
    print('Reason: ' + str(resp.text))

# Kolorowanie tekstu w konsoli
class bcolors:
    HEADER = '\033[95m'
    INFO = '\033[94m'
    OKGREEN = '\033[92m'
    OKBLUE = '\033[96m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    FAIL = '\033[91m\033[0m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SubMode(Cmd):
    """
    Implements the basic commands for all modes
    """
    # Docs for help method
    docs={
        'show': {
                    'app': 'Application Profiles',
                    'bridgedomain': 'Wyświetl bridge domeny',
                    'context': 'Wyświetl konteksty',
                    'contract': 'Wyświetl kontrakty',
                    'epg': 'Wyświetl epg',
                    'infradomains': 'Wyświetl domeny',
                    'inventory': 'Wyświetl dane fabryki',
                    'interface': 'Wyświetl szczegóły interfejs',
                    'mac': 'znjadz maki ',
                    # 'ip': 'znajdź endpointy po adresie IP',
                    'port-channel': 'Wyświetl listę port-channeli',
                    'tag': 'Wyświetl tagi',
                    'tenants': 'Wyświetl listę tenantów',
                    'cdp': 'Wyświetl szczegóły CDP',
                    'lldp': 'Wyświetl szczegóły LLDP'
                    # 'faults': 'Pokaż błędy'
        },
        'cdp': {
            'neighbours': 'Wyświetl sąsiadów CDP'
        },
        'lldp': {
            'neighbours': 'Wyświetl sąsiadów LLDP'
        },
        'mac': {
            'show mac address epg [Tenant]:[APP]:[EPG] (np. TEST:OCP:Vlan801) ->  ': 'wyszukaj wszystkie adresy w danym epg',
            'show mac address 00:50:56:9F:01:84  ->  ': 'znadjź konkretny adres',
        },
        'interface':{
            'show interface eth 1/101/1/1  ': 'Wyświetl szczegóły interejsu [Typ pod/node(leaf)/module/port]',
            'show interface description leaf 101 ': 'Wyświetl opisy interfejsów na leafie 101',
            'show interface description include nazwa ': 'Wyszukiwanie w lokalnej bazie danych interfejsów zawierających w opisie portu ciąg znaków',
            'show interface description include nazwa online': 'Wyszukiwanie online interfejsów zawierających w opisie portu ciąg znaków'
        },
        # 'ip':{
        #     'show ip address [x.x.x.x]  ->  ': 'znadjź konkretny adres',
        # },
        'port-channel': {
            'show port-channel':    'Wyświetla skonfigurowane VPC Policy Groups',
            'show port-channel summary leaf [leaf_nr]': 'Wyświetla listę oraz status port-channel na leaf (np. leaf 101)'
        },
        'neighbours':{
            'cdp': 'Wyświetl sąsiadów CDP',
            'lldp': 'Wyświetl sąsiadów LLDP'
        },
        'inventory':{
            'media leaf 201': 'Wyświetl wszystkie wkładki SFP w leafie',
            'media': 'Wyświetl wszystkie wkładki SFP w fabryce'
        },
        'audit':{
            'logs': 'Wyświetl dane audit logs'
        },
        'switchback': {'': 'Switch back out of a particular tenant'}
    }

    def __init__(self):
        Cmd.__init__(self)
        self.tenant = None
        self.app = None
        self.epg = None
        self.contract = None
        self.set_prompt()
        self.negative = False
        self.apic = None

    def set_prompt(self):
        """ Should be overridden by inheriting classes """
        pass

    def do_show(self, args, to_return=False):
        """ Pokaż informacje z systemu ACI"""

        words = args.strip().split(' ')

        if words[0] == 'tenants':
            logging.info('show '+words[0])
            tenants = Tenant.get(self.apic)
            tenant_dict = {}
            for tenant in tenants:
                tenant_dict[tenant.name] = []
            if to_return:
                return tenant_dict
            print('Tenant')
            print('------')
            for tenant in tenants:
                print(tenant.name)


        elif words[0] == 'inventory':
            logging.info('show '+words[0])
            if '?' in words:
                self.do_help(' '.join(words))
                return ''

            if len(words) >= 2:
                print('Zbieram dane...')
                inventory = CollectInventory(self.apic, logging, bcolors)
                if words[1] == 'media' and len(words) == 2:
                    sfps = inventory.get_all_inserted_sfps()

                elif len(words) == 4 and words[2] == 'leaf':
                    sfps = inventory.get_all_inserted_sfps(words[3])

                else:
                    self.do_help(' '.join(words))
                    return ''

                print('\n')
                headers=['Leaf', 'Port', 'Typ', 'PartNumber', 'SerialNumber', 'ReV']
                print tabulate(sfps, headers, tablefmt="github")
                print('\n')

        elif words[0] == 'bridgedomain':
            logging.info('show '+words[0])
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                bds = BridgeDomain.get(self.apic, tenant)
                bd_dict = {}
                bd_dict[tenant.name] = []
                for bd in bds:
                    bd_dict[tenant.name].append(bd.name)
                if to_return:
                    return bd_dict
                for bd in bds:
                    output.append((tenant.name, bd.name))
            print tabulate(output, headers=['Tenant', 'BridgeDomain'], tablefmt="github")

        elif words[0] == 'context':
            logging.info('show '+words[0])
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                contexts = Context.get(self.apic, tenant)
                for context in contexts:
                    output.append((tenant.name, context.name))
            print tabulate(output, headers=['Tenant', 'Context'], tablefmt="github")

        elif words[0] == 'contract':
            logging.info('show '+words[0])
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [self.tenant]
            output = []
            for tenant in tenants:
                contracts = Contract.get(self.apic, tenant)
                for contract in contracts:
                    output.append((tenant.name, contract.name))
            print tabulate(output, headers=['Tenant', 'Contract'], tablefmt="github")

        elif words[0] == 'port-channel':
            logging.info('show '+words[0])
            if '?' in words:
                self.do_help(' '.join(words))
                return ''

            if len(words) > 2:
                portchannels = InterfaceCollector(self.apic, logging, bcolors)
                # try:
                if words[1] == 'summary':
                    if words[2] == 'leaf' and words[3]:
                        logging.info('show '+words[0]+words[1]+words[2]+words[3])
                        # portchannels.show_summary()
                        portchannels.show_summary(node=words[3])
                        # portchannels._get_member_extension('po16')

                elif words[1] == 'test':
                    portchannels.test()
                else:
                    logging.info('Nieokreślony błąd')
                    print ('% Incomplete command\n')
                    self.do_help(' '.join(words))
                # except:
                #     logging.info(bcolors.WARNING + '% Unrecognized command\n')
                #     print ('% Unrecognized or Incomplete command\n')
                #     self.do_help(' '.join(words))

            elif len(words) == 1:
                portchannels = PortChannel.get(self.apic)
                print('Port Channel')
                data = []
                for pc in portchannels:
                    pc._update_nodes()
                    data.append([
                        pc,
                    ])
                print tabulate(data, headers=['Name'], tablefmt="github")
            else:
                print ('% Unrecognized command\n')
                self.do_help(' '.join(words))

        elif words[0] == 'tag':
            logging.info('show '+words[0])
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            output = []
            if len(words) == 2:
                if words[1] == 'epg':
                    for tenant in tenants:
                        apps = AppProfile.get(self.apic, tenant)
                        for app in apps:
                            epgs = EPG.get(self.apic, app, tenant)
                            for epg in epgs:
                                tag_list = Tag.get(self.apic, parent=epg, tenant=tenant)
                                if len(tag_list):
                                    tag_list = [tag.name for tag in tag_list]
                                    if len(tag_list):
                                        output.append((tenant.name, app.name, epg.name, ",".join(tag_list)))

                    print tabulate(output, headers=["Tenant",
                                          "App",
                                          "EPG",
                                          "Tag"], tablefmt="github")

                elif words[1] == 'bd':
                    print("bd")
            else:
                for tenant in tenants:
                    tag_list = Tag.get(self.apic, parent=tenant, tenant=tenant)
                    tag_list = [tag.name for tag in tag_list]
                    if len(tag_list):
                        output.append((tenant.name, ",".join(tag_list)))
                print tabulate(output, headers=["Tenant", "Tag"], tablefmt="github")

        elif words[0] == 'app':
            logging.info('show '+words[0])
            if self.tenant is None:
                tenants = Tenant.get(self.apic)
            else:
                tenants = [Tenant(self.tenant.name)]
            output = []
            for tenant in tenants:
                apps = AppProfile.get(self.apic, tenant)
                for app in apps:
                    if tenant is not None and tenant != app.get_parent():
                        continue
                    output.append((app.get_parent().name, app.name))

            print tabulate(output, headers=['Tenant', 'App Profile'], tablefmt="github")

        elif words[0] == 'epg':
            logging.info('show '+words[0])
            epg_dict = self.sh_epg()
            print('\n[Tenant]:\n    [APP]:\n        -[EPG]\n')
            print yaml.dump(epg_dict, default_flow_style=False)

        elif words[0] == 'cdp':
            logging.info('show '+words[0])
            if '?' in words:
                self.do_help(' '.join(words))
                return ''
            elif len(words) < 2:
                print('% Incomplete command.')
                return ''

            # if some arguments exist
            if words[1] == 'neighbours':
                logging.info('show '+words[0]+words[1])
                logging.info("sh_cdp")
                print(" Zbieram dane... (to może chwilkę potrwać..)")
                neighbours = NEIGHBOURS(self.apic, logging, bcolors)
                print tabulate(neighbours.cdp(), headers=["Node-ID",
                                                     "Local Interface",
                                                     "Neighbour Device",
                                                     "Neighbour Platform",
                                                     "Neighbour Interface"], tablefmt="github")

        elif words[0] == 'lldp':
            logging.info('show '+words[0])
            if '?' in words:
                self.do_help(' '.join(words))
                return ''
            elif len(words) < 2:
                print('% Incomplete command.')
                return ''

            if words [1] == 'neighbours':
                logging.info('show '+words[0]+words[1])
                print(" Zbieram dane... (to może chwilkę potrwać..)")
                neighbours = NEIGHBOURS(self.apic, logging, bcolors)
                print tabulate(neighbours.lldp(), headers=["Node-ID",
                                                     "Local Interface",
                                                     "Ip",
                                                     "Name",
                                                     "Chassis_id_t",
                                                     "Neighbour Platform",
                                                     "Neighbour Interface"], tablefmt="github")

        elif words[0] == 'mac':
            logging.info('show '+words[0])
            # if user put ? in line do help method
            if '?' in words:
                self.do_help(' '.join(words))
                return ''
            elif len(words) < 2:
                print('% Incomplete command.')
                return ''
            # if some arguments exist
            if words[1] == 'address':
                try:
                    mac_check = re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", str(words[2]))
                    mac_ios_style = re.match(r"^([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})$", str(words[2]))
                    if mac_check:
                        logging.info(mac_check.group(0))
                        self.find_address(mac=words[2])
                    elif mac_ios_style:
                        logging.info(mac_ios_style.group(0))
                        self.find_address(mac=words[2])
                    elif words[2] == 'epg':
                        if words[-1] != 'epg':
                            self.find_address(epg=words[3])
                        else:
                            self.do_help(' '.join(words))
                except:
                    logging.error("Nieoczekiwany błąd ")
                    self.do_help(' '.join(words))

        elif words[0] == 'interface':
            logging.info('show '+words[0])
            if '?' in words:
                self.do_help(' '.join(words))
                return ''
            elif len(words) < 2:
                print('% Incomplete command.')
                return ''

            if words[1] == 'eth':
                # try:
                ifname = ' '.join(words[1:])
                logging.info(bcolors.INFO +'Przekazuję zmienną '+ ifname)
                inf = INTERFACE(self.apic, logging, bcolors)
                inf_details = inf.sh_interface_detail(ifname)
                print (inf_details)
                # except:
                #     logging.warning('Nieznany błąd')
                #     print ('Nieznany błąd')



            # elif words[1] == 'test':
            #     ifname = ' '.join(words[2:])
            #     inf = INTERFACE(self.apic, logging, bcolors)
            #     # inf_details = inf.test('eth 2/207/1/10')
            #     inf_details = inf.test(ifname)

            elif words[1] == 'statistics' and len(words) == 3:
                try:
                    logging.info('show '+words[0]+words[1]+words[2])
                    int_stats = INTERAFES_STATS(self.apic, logging, bcolors)
                    int_stats.get_stats(words[2])
                except:
                    logging.info('Nieznany błąd')
                    print('% Syntax error.')
                    return ''

            elif len(words) == 4 and words[1] == 'description' and words[2] == 'leaf':
                int = INTERFACE(self.apic, logging, bcolors)
                apic_intf_classes = ['l1PhysIf', 'pcAggrIf']
                for apic_intf_class in apic_intf_classes:
                    print (apic_intf_class)
                    int.show_interface_description(words[3], apic_intf_class=apic_intf_class)

            elif len(words) == 4 and words[1] == 'description' and words[2] == 'include':
                results = []
                headers = ["Leaf", "Port", "Type", "Speed", "Description"]
                int = INTERFACE(self.apic, logging, bcolors)
                # int.search_interface_by_description(words[3], False)
                logging.info('search_interface_by_description '+words[3])
                print ('\n')
                print(tabulate(int.search_interface_by_description(words[3], False), headers=headers, tablefmt="github"))

            elif len(words) == 5 and words[1] == 'description' and words[2] == 'include' and words[4] == 'online':
                logging.info('search_interface_by_description_online '+words[3])
                results = []
                headers = ["Leaf", "Port", "Type", "Speed", "Description"]
                int = INTERFACE(self.apic, logging, bcolors)
                apic_intf_classes = ['l1PhysIf']
                for apic_intf_class in apic_intf_classes:
                    print ('\n')
                    print(tabulate(int.search_interface_by_description(words[3], apic_intf_class), headers=headers, tablefmt="github"))

            else:
                logging.info(words)
                logging.info(words[1])
                logging.info(len(words))
                print('% Incomplete command.')
                self.do_help(' '.join(words))
                return ''

        elif words[0] == 'infradomains':
            logging.info('show '+words[0])
            infradomains = PhysDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('---------------')
                print('Physical Domain')
                print('---------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = []
            infradomains = VmmDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('----------')
                print('VMM Domain')
                print('----------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = L2ExtDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('------------------')
                print('L2 External Domain')
                print('------------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = L3ExtDomain.get(self.apic)

            output = []
            association = ''
            if len(infradomains) > 0:
                print('------------------')
                print('L3 External Domain')
                print('------------------')

            for domain in infradomains:
                print(domain.name)

            if len(infradomains) > 0:
                print('\n')

            infradomains = EPGDomain.get(self.apic)

            for domain in infradomains:
                association = domain.tenant_name + ':' + domain.app_name + ':' + domain.epg_name
                output.append((domain.domain_name, domain.domain_type,
                               association))

            if len(infradomains) > 0:
                template = '{0:20} {1:11} {2:26}'
                print(template.format('Infra Domain Profile', 'Domain Type', 'TENANT:APP:EPG Association'))
                print(template.format('--------------------', '-----------', '--------------------------'))
                for rec in output:
                    print(template.format(*rec))
                print('\n')

        else:
            sys.stdout.write('%% Unrecognized command\n')

    def sh_epg(self):
        epg_dict = {}
        if self.tenant is None:
            tenants = Tenant.get(self.apic)
        else:
            tenants = [Tenant(self.tenant.name)]
        for tenant in tenants:
            apps = AppProfile.get(self.apic, tenant)
            for app in apps:
                epgs = EPG.get(self.apic, app, tenant)
                for epg in epgs:
                    assert app == epg.get_parent()
                    app = epg.get_parent()
                    if app is not None:
                        tenant = app.get_parent()
                    if self.app is not None and self.app != app:
                        continue
                    if self.tenant is not None and self.tenant != tenant:
                        continue

                    if unicode(tenant.name) not in epg_dict.keys():
                        epg_dict[tenant.name] = {}
                    if app.name not in epg_dict[tenant.name]:
                        epg_dict[tenant.name][app.name] = []
                    epg_dict[tenant.name][app.name].append(epg.name)
        if epg_dict:
            # logging.info(epg_dict)
            return epg_dict
            # print('\n[Tenant]:\n    [APP]:\n        -[EPG]\n')
            # print yaml.dump(epg_dict, default_flow_style=False)
        else:
            logging.error("Błąd w wyszukiwaniu EPG")

    def emptyline(self):
        pass

    def complete_show(self, text, line, begidx, endidx):
        " Complete the show command "
        show_args = ['bridgedomain ', 'context ', 'contract ', 'app ',
                     'port-channel ', 'epg ', 'infradomains ', 'interface ',
                     'tenants ', 'tag ', 'mac ', 'faults ', 'cdp ', 'lldp ', 'inventory ']
        completions = [a for a in show_args if a.startswith(line[5:])]

        words = line.strip().split(' ')
        if len(words) < 2:
            return completions

        elif any(s.lower() == 'mac' for s in words) and any(s.lower() == 'address' for s in words) and any(s.lower() == 'epg' for s in words):
            args = [a for a in self.do_show('epg', to_return=True).keys()]
            # completions = [a for a in switchto_args if a.startswith(line[9:])]

            return [
                arg for arg in agrs
                if arg.startswith(text)
            ]

        elif any(s.lower() == 'mac' for s in words) and any(s.lower() == 'address' for s in words):
            mac_agrs = [
                'epg',
            ]
            return [
                arg for arg in mac_agrs
                if arg.startswith(text)
            ]
        elif any(s.lower() == 'mac' for s in words):
            mac_agrs = [
                'address'
            ]
            return [
                arg for arg in mac_agrs
                if arg.startswith(text)
            ]
        # elif words[1] == 'ip':
        #     ip_agrs = [
        #         'address',
        #     ]
        #     return [
        #         arg for arg in ip_agrs
        #         if arg.startswith(text)
        #     ]
        elif any(s.lower() == 'port-channel' for s in words):
            agrs = [
                'summary leaf '
            ]
            return [
                arg for arg in agrs
                if arg.startswith(text)
            ]
        elif words[1] == 'cdp' or words[1] == 'lldp':
            agrs = [
                'neighbours'
            ]
            return [
                arg for arg in agrs
                if arg.startswith(text)
            ]
        elif any(s.lower() == 'interface' for s in words) and any(s.lower() == 'description' for s in words) and any(s.lower() == 'include' for s in words):
                agrs = [
                    'online '
                ]
                return [
                    arg for arg in agrs
                    if arg.startswith(text)
                ]
        elif any(s.lower() == 'interface' for s in words) and any(s.lower() == 'description' for s in words):
                agrs = [
                    'leaf ',
                    'include '
                ]
                return [
                    arg for arg in agrs
                    if arg.startswith(text)
                ]
        elif words[1] == 'interface':
            agrs = [
                'description '
            ]
            return [
                arg for arg in agrs
                if arg.startswith(text)
            ]
        elif words[1] == 'inventory':
            ip_agrs = [
                'media',
            ]
            return [
                arg for arg in ip_agrs
                if arg.startswith(text)
            ]

        return completions

    def do_exit(self, args):
        " Exit the command mode "
        return -1

    def precmd(self, line):
        """precmd"""
        # Check for negative of the command (no in front)
        if line.strip()[0:len('no')] == 'no':
            line = line.strip()[len('no'):]
            self.negative = True
        else:
            self.negative = False

        if line.strip() == 'help':
            sys.stdout.write('%s\n' % self.__doc__)
            return ''
        cmd, arg, line = self.parseline(line)
        if arg == '?':
            self.do_help(line)
            cmds = self.completenames(cmd)
            if cmds:
                self.columnize(cmds)
                sys.stdout.write('\n')
            return ''
        return line

    def get_args_num_nth(self, text, line, nth='last'):
        """get_args_num_nth"""
        args = line.split()
        # the number of completed argument
        num_completed_arg = len(args) - 1 if text == args[len(args) - 1] else len(args)
        # the last completed argument
        first_cmd = args[0]
        last_cmd = args[num_completed_arg - 1]
        try:
            nth_cmd = args[nth]
        except (TypeError, IndexError):
            nth_cmd = args[num_completed_arg - 1]
        return args, num_completed_arg, first_cmd, nth_cmd, last_cmd

    def get_args_num_last(self, text, line):
        """get_args_num_last"""
        args = line.split()
        # the number of completed argument
        num_completed_arg = len(args) - 1 if text == args[len(args) - 1] else len(args)
        # the last completed argument
        last_completed_arg = args[num_completed_arg - 1]
        return args, num_completed_arg, last_completed_arg

    def get_completions(self, text, array):
        """get_completions"""
        if args == '':
            return array
        return [a for a in array if a.startswith(text)]

    def get_operator_port(self, line, arg):
        """get_operator_port"""
        line = line.split(' ')
        if arg in line:
            index = line.index(arg)
            return line[index + 1:index + 3]

    def filter_args(self, black_list, array):
        """filter_args"""
        if type(black_list) == str:
            black_list = black_list.split()
        return list(set(array) - set(black_list) & set(array))

    def do_help(self, arg):

        words = arg.strip().split(' ')
        if words[0] == '':
            doc_strings = [(i[3:], getattr(self, i).__doc__)
                           for i in dir(self) if i.startswith('do_')]
            doc_strings = ['  {!s:12}\t{!s}\n'.format(i, j)
                           for i, j in doc_strings if j is not None]

            sys.stdout.write('Skorzystaj z pomocy online: ')
            print("%s" % ('https://wiki/display/ACIWiki/Funkcje+systemu'))

            sys.stdout.write('\nDostępne polecenia:\n%s\n' % ''.join(doc_strings))
        elif words[0] not in self.docs.keys():
            print "Not found"
            return ''
        else:
            # help docs for commands
            doc_strings = ['  {!s:12}\t{!s}\n'.format(i, j)
                           for i, j in self.docs[words[0]].items()]
            sys.stdout.write('Help:\n%s\n' % ''.join(doc_strings))
            return ''


class AdminSubMode(SubMode):
    """Administration submode"""
    def __init__(self, apic=None):
        SubMode.__init__(self)
        self.set_prompt()
        self.apic = apic
        self.new_apic_login = False

    def set_prompt(self):
        self.prompt = 'ACI_CLI'
        self.prompt += '(admin)# '

    def set_apic(self, apic=None):
        """set the apic"""
        print ('Tryb podwyższonych uprawnień')
        print ('Wprowadź uprawnienia administratora\n')
        if apic:
            self.apic = apic
        else:
            new_LOGIN = raw_input('Login: ')
            new_PASSWORD = getpass.getpass('Password: ')
            self.apic = Session(URL, new_LOGIN, new_PASSWORD)
            try:
                logging.info(bcolors.INFO +'Próba połączenia do '+URL+' użytkownik: '+new_LOGIN)
                resp = self.apic.login()

                if resp.status_code != 200:
                    logging.error(bcolors.FAIL  +'Nie mogę połączyć APIC '+URL)
                    print('%% Nie mogę połączyć APIC '+URL)
                    sys.exit(2)
                    pass

                self.new_apic_login = True

            except requests.exceptions.ConnectionError:
                print('%% Nie mogę połączyć APIC '+URL)
                sys.exit(2)
                pass

            except requests.exceptions.MissingSchema:
                print('%% Invalid URL.')
                sys.exit(2)
                pass

    def do_audit(self, args):
        """ Wyświetl audit logs | format: audit logs """
        if not self.apic:
            self.set_apic()

        args = args.split()
        if len(args) == 0:
            print('%% audit command requires the following '
                  'format: audit logs')
            return

        elif args[0] == 'logs':
            auditlog = AuditLog(self.apic, None, logging, bcolors)
            auditlog.get_audit_logs()

    def do_exit(self, args=None):
        print (args)
        " Wyjdź z trybu administratora "
        # Sprawdź czy nastąpiła zmiana LOGOWANIA do apic
        if self.new_apic_login:
            # logout from apic
            logging.info('Logout from APIC')
            self.apic.close()
            self.apic = Session(URL, LOGIN, PASSWORD)
            try:
                logging.info(bcolors.INFO +'Próba połączenia do '+URL+' użytkownik: '+LOGIN)
                resp = self.apic.login()

                if resp.status_code != 200:
                    logging.error(bcolors.FAIL  +'Nie mogę połączyć APIC '+URL)
                    sys.exit(2)
                    pass
            except requests.exceptions.ConnectionError:
                print('%% Nie mogę połączyć APIC '+URL)
                sys.exit(2)
                pass

            except requests.exceptions.MissingSchema:
                print('%% Invalid URL.')
                sys.exit(2)

        return -1

class CmdLine(SubMode):

    """
    Help is available through '?'
    """

    def __init__(self):
        Cmd.__init__(self)
        self.apic = apic
        if not READLINE:
            self.tekey = None
        self.tenant = None
        self.app = None
        self.epg = None
        self.set_prompt()
        self.intro = ('\nACI CLI - Commands Shell v1.1.5\nemail: kaszlikowski.s@gmail.com\n#Na podstawie Cisco ACI Toolkit Command Shell\nW celu pomocy naciśnij ?\n\n')

        self.negative = False
        self.adminsubmode = AdminSubMode()
        self.adminsubmode.promt = self.prompt

    def set_prompt(self):

        if URL == 'https://sandboxapicdc.cisco.com':
            self.prompt = '\033[93m ACI_CLI_SANDBOX\033[00m'
        elif URL == 'https://<APIC PROD ADDTESS>':
            self.prompt = 'ACI_CLI_PROD'

        if self.tenant is not None:
            self.prompt += '-' + self.tenant.name
        self.prompt += '# '

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        logging.info(cmd)
        logging.info(arg)
        logging.info(str(line))
        # cmds = self.tenames(cmd)
        cmds = line.split(" ")
        num_cmds = len(cmds)

        if num_cmds == 1:
            try:
                getattr(self, 'do_' + cmds[0])(arg)
            except:
                sys.stdout.write('% Unrecognized command\n')
        elif num_cmds > 1:
            sys.stdout.write('%% Ambiguous command:\t"%s"\n' % cmd)
        else:
            sys.stdout.write('% Unrecognized command\n')

    def do_help(self, arg):

        words = arg.strip().split(' ')
        if words[0] == '':
            doc_strings = [(i[3:], getattr(self, i).__doc__)
                           for i in dir(self) if i.startswith('do_')]
            doc_strings = ['  {!s:12}\t{!s}\n'.format(i, j)
                           for i, j in doc_strings if j is not None]

            sys.stdout.write('\nDostępne polecenia:\n%s\n' % ''.join(doc_strings))
        elif words[0] not in self.docs.keys():
            print "Not found"
            return ''
        else:
            # help docs for commands
            doc_strings = ['  {!s:12}\t{!s}\n'.format(i, j)
                           for i, j in self.docs[words[0]].items()]
            sys.stdout.write('Help:\n%s\n' % ''.join(doc_strings))
            return ''

    def completedefault(self, text, line, begidx, endidx):
        error = 'text: ' + str(text) + ' line: ' + str(line) + ' begidx: ' + str(begidx) + ' endidx: ' + str(endidx)
        logging.info(str(error))
        print ('Nie znaleziono polecenia\n')

    def do_EOF(self, line):
        return True

    def find_address(self, **kwargs):
        " Find mac or ip address "
        endpoints = ENDPOINTS(self.apic, self.tenant, logging, bcolors)

        for key, value in kwargs.items():
            if key == 'mac':
                " Find macs "
                logging.info(bcolors.INFO +'Szukam maków')
                endpoints.get_endpoints(mac=value)
                print tabulate(endpoints.endpoints_data, headers=['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
                           'Encap'], tablefmt="github")
                print ("\n")

            elif key == 'ip':
                " Find ipv4 ipaddress "
                logging.info(bcolors.INFO + "Szukam ipków ")
                print ('Funkcja w trakcie budowy')
                # if value[0] == 'pod':
                #     logging.info(value)
                #     endpoints.addres(pod=value[1])
                # else:
                #     logging.info(value)
                #     endpoints.addres(addr=value[0])
                #
                # if endpoints.endpoints_data:
                #     print tabulate(endpoints.endpoints_data, headers=['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
                #                'Encap'], tablefmt="github")
                #     print ("\n")
                # else:
                #     print tabulate("", headers=['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
                #                'Encap'])
                #     print ("Brak wyników")

            elif key == 'epg':
                # endpoints.get_endpoints(epg=value)
                print tabulate(endpoints.get_endpoints(epg=value), headers=['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', '', ''], tablefmt="github")
                print ("\n")
            else:
                print ("Can't find")

    def do_switchto(self, args):
        " Przełącz do wybranego tenantu "
        if self.negative:
            return
        if len(args.split()) > 1 or len(args.split()) == 0:
            sys.stdout.write('%% switchto tenant requires 1 tenant-name\n')
            return
        tenant = Tenant(args.strip())
        if Tenant.exists(self.apic, tenant):
            self.tenant = Tenant(args.strip())
            self.set_prompt()
        else:
            print('%% Tenant %s does not exist' % tenant.name)

    def complete_switchto(self, text, line, begidx, endidx):
        """
        Switch to a particular tenant
        :return: List of possible tenants for completions
        """
        switchto_args = [a for a in self.do_show('tenants',
                                                 to_return=True).keys()]
        completions = [a for a in switchto_args if a.startswith(line[9:])]
        return completions

    def do_switchback(self, args):
        " Powrót z trybu tenantu "
        if len(args.split()) > 0:
            sys.stdout.write('%% switchback has no extra parameters\n')
            return
        self.tenant = None
        self.set_prompt()

    def do_exit(self, args):
        " Wyjdź "
        return -1

    def do_clear(self, args):
        " Wyczyść ekran "
        system('clear')
        return ''

    def do_admin(self, args):
        " Wejdź do trybu administratora "
        if self.negative:
            return
        self.adminsubmode.set_prompt()
        self.adminsubmode.cmdloop()

    def complete_configure(self, text, line, begidx, endidx):
        """
        Complete the configuration commands
        :return: List of strings that can be completed
        """
        print ('hello')
        completions = ['terminal']
        return completions


# class MockStdin(object):


def main(apic):
    """
    Main execution routine

    :param apic: Instance of Session class
    """
    print ("\033[92m          _|_|      _|_|_|  _|_|_| ")
    print ("        _|    _|  _|          _|    ")
    print ("        _|_|_|_|  _|          _|    ")
    print ("        _|    _|  _|          _|    ")
    print ("        _|    _|    _|_|_|  _|_|_| ")
    print ("\n")
    print ("\033[00m")


    cmdLine = CmdLine()
    cmdLine.apic = apic
    cmdLine.cmdloop()


# *** MAIN LOOP ***
if __name__ == '__main__':
    system('clear')

    OUTPUTFILE = ''
    DEBUGFILE = 'acicli.log'
    # DEBUGFILE = None
    DEBUGLEVEL = logging.INFO
    # DEBUGLEVEL = logging.WARNING
    usage = ('Usage: acicli.py -l <login> -p <password> -u <url> '
             '[-o <output-file>] [-t <test-file>]')
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hl:p:u:do:f:t:",
                                   ["help", "enable-debug",
                                    "output-file=", "debug-file=",
                                    "test-file="])
    except getopt.GetoptError:
        print(str(sys.argv[0]) + ' : illegal option')
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(usage)
            sys.exit()

        elif opt in ('-o', '--output-file'):
            OUTPUTFILE = 'logs.txt'
        elif opt in ('-d', '--enable-debug'):
            DEBUGFILE = None
            DEBUGLEVEL = logging.DEBUG
        # elif opt in ('-f', '--debug-file'):
        #     DEBUGFILE = arg
        elif opt in ('-t', '--test-file'):
            TESTFILE = arg

    if URL == '' or LOGIN == '' or PASSWORD == '':
        print(usage)
        sys.exit(2)

    logging.basicConfig(format=(bcolors.OKGREEN+'     %(asctime)s   %(levelname)s:[%(lineno)d:%(module)s:'
                                '%(funcName)s]:  %(message)s'+bcolors.ENDC),
                        datefmt='%d/%m/%Y %I:%M:%S %p',
                        filename=DEBUGFILE, filemode='a+',
                        level=DEBUGLEVEL)

    apic = Session(URL, LOGIN, PASSWORD)
    try:
        logging.info(bcolors.INFO +'Próba połączenia do '+URL+' użytkownik: '+LOGIN)
        resp = apic.login()

        if resp.status_code != 200:
            logging.error(bcolors.FAIL  +'Nie mogę połączyć APIC '+URL)
            sys.exit(2)
            pass

    except requests.exceptions.ConnectionError:

        print('%% Nie mogę połączyć APIC '+URL)
        sys.exit(2)
        pass

    except requests.exceptions.MissingSchema:
        print('%% Invalid URL.')
        sys.exit(2)

    if 'TESTFILE' in locals():
        sys.stdin = MockStdin(TESTFILE, sys.stdin)

    try:
        main(apic)
    except KeyboardInterrupt:
        pass
