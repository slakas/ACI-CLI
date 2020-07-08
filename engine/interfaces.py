#!/usr/bin/env python
# -*- encoding: utf-8 -*-
### INTERFACEs MODULE


from operator import attrgetter
import engine.acitoolkit.acitoolkit as aci
from tabulate import tabulate
from portchannel import InterfaceCollector
import re
import time
import sys
import sqlite3

class INTERFACE():
    """docstring for Interface."""

    def __init__(self, session, logging, bcolors):
        self.endpoints_data = []
        # session to APIC
        self.session = session
        # get Intercaes
        # self.interfaces = aci.Interface.get(self.session)

        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def _get_query(self, query_url, error_msg):
        resp = self.session.get(query_url)
        if not resp.ok:
            print(error_msg)
            print(resp.text)
            return False

        if resp.json()['totalCount'] == '0':
            self.logging.warning ('% Wystąpił błąd. Sprawdź dane i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return False

        elif resp.json()['imdata'][0].keys()[0] == 'error':
            self.logging.warning ('% Wystąpił błąd. Sprawdź dane i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return False

        return resp.json()

    def sh_interfaces(self):
        # Tymczasowo wyłączony
        return ""
        data = []
        self.logging.info("Show interfaces")
        for interface in self.interfaces:
            data.append((interface.attributes['if_name'],
                         interface.attributes['porttype'],
                         interface.attributes['adminstatus'],
                         interface.attributes['operSt'],
                         interface.attributes['operSpeed'],
                         interface.attributes['usage'],
                         interface.attributes['descr']))

        # Display the data downloaded
        template = "{0:17} {1:6} {2:^11} {3:^6} {4:7} {5:21} {6:^11}"
        print(template.format("INTERFACE", "TYPE", "ADMIN-STATE", "OPER", "SPEED", "USAGE", "DESCRIPTION"))
        print(template.format("---------", "----", "-----------", "------", "-----", "---------------------", "-----------"))
        for rec in data:
            print(template.format(*rec))
        return ""

    def get_interface_phys_detail(self, **kwargs):
        # Prametry fizyczne portu
        #         print ("\nPhysical detalis")

        pod = kwargs['pod']
        node_id = kwargs['node_id']
        slot = kwargs['slot']
        port_id = kwargs['port_id']
        port = slot+'/'+port_id
        phys = {}


        url = ('/api/mo/topology/pod-'+pod+'/node-'+node_id+'/sys/phys-[eth'+port+'].json?query-target=subtree'
                     '&target-subtree-class=l1PhysIf')
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        l1PhysIf = self._get_query(url, error_message)

        if l1PhysIf is False:
            self.logging.warning('l1PhysIf Get API error')
            return None

        if l1PhysIf['totalCount'] == '1':
            # print ("\nPhysical detalis")
            attr = l1PhysIf['imdata'][0]['l1PhysIf']['attributes']
            phys.update({'id': attr['id']})
            if attr['adminSt'] == 'up':
                phys.update({'adminSt': '\033[92m'+attr['adminSt']+'\033[00m'})
            else:
                phys.update({'adminSt': '\033[91m'+attr['adminSt']+'\033[00m'})

            if attr['switchingSt'] == 'enabled':
                phys.update({'switchingSt': '\033[92m'+attr['switchingSt']+'\033[00m'})
            else:
                phys.update({'switchingSt': '\033[91m'+attr['switchingSt']+'\033[00m'})
            phys.update({'autoNeg': attr['autoNeg']})
            phys.update({'bw': attr['bw']})
            phys.update({'descr': attr['descr']})
            phys.update({'layer': attr['layer']})
            phys.update({'mode': attr['mode']})
            phys.update({'mtu': attr['mtu']})
            phys.update({'portT': attr['portT']})
            phys.update({'speed': attr['speed']})
            phys.update({'usage': attr['usage']})

            # Led flash color
            url = ('/api/mo/topology/pod-'+pod+'/node-'+node_id+'/sys/ch/lcslot-'+slot+'/lc/leafport-'+port_id+'.json?query-target=subtree')
            error_message = 'Could not collect APIC data for switch %s.' % node_id
            eqptLC = self._get_query(url, error_message)

            if eqptLC['totalCount'] >= '1':
                # Led flash color
                if 'eqptIndLed' in eqptLC['imdata'][0].keys():
                    self.logging.info('eqptIndLed')
                    eqptIndLed_attr = eqptLC['imdata'][0]['eqptIndLed']['attributes']
                    if eqptIndLed_attr['color'] == 'yellow':
                        phys.update({'color-LED': '\x1b[5;30;43m'+eqptIndLed_attr['color']+'\033[00m'})

                    if eqptIndLed_attr['color'] == 'green':
                        phys.update({'color-LED': '\x1b[5;30;42m'+eqptIndLed_attr['color']+'\033[00m'})

            # More interfaces info
            url_val = ('topology/pod-'+pod+'/node-'+node_id+'/sys/phys-[eth'+port+']/phys')
            url = ('/api/node/class/ethpmPhysIf.json?query-target-filter=and(eq(ethpmPhysIf.dn,"'+url_val+'"))')
            error_message = 'Could not collect APIC data for switch %s.' % node_id
            ethpmPhysIf = self._get_query(url, error_message)
            if ethpmPhysIf['totalCount'] >= '1':
                ethpm_attr = ethpmPhysIf['imdata'][0]['ethpmPhysIf']['attributes']
                phys.update({'backplaneMac': ethpm_attr['backplaneMac']})
                lastLinkStChg_date = time.strptime(ethpm_attr['lastLinkStChg'][:19], "%Y-%m-%dT%H:%M:%S")
                phys.update({'lastLinkStChg': time.strftime("%Y-%m-%d %H:%M:%S", lastLinkStChg_date)})
                if ethpm_attr['operSt'] == 'down':
                    phys.update({'operSt': '\033[91m'+ethpm_attr['operSt']+'\033[00m'})
                    phys.update({'operStQual': ethpm_attr['operStQual']})
                else:
                    phys.update({'operSt': '\033[92m'+ethpm_attr['operSt']+'\033[00m'})

        return phys

    def get_interface_media(self, **kwargs):
        # Właściwości wkładki sfp
        pod = kwargs['pod']
        node_id = kwargs['node_id']
        slot = kwargs['slot']
        port_id = kwargs['port_id']
        port = slot+'/'+port_id
        ethpm = {}

        url = ('/api/mo/topology/pod-'+pod+'/node-'+node_id+'/sys/phys-[eth'+port+']/phys.json?query-target=subtree'
                     '&target-subtree-class=ethpmFcot')
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        ethpmFcot = self._get_query(url, error_message)
        if not ethpmFcot:
            self.logging.warning(error_message)
            return None

        if ethpmFcot['totalCount'] != '0':
            attr = ethpmFcot['imdata'][0]['ethpmFcot']['attributes']
            if attr['state'] == 'inserted':
                ethpm.update({'guiCiscoEID': attr['guiCiscoEID']})
                ethpm.update({'guiName': attr['guiName']})
                ethpm.update({'guiPN': attr['guiPN']})
                ethpm.update({'guiRev': attr['guiRev']})
                ethpm.update({'guiSN': attr['guiSN']})
                ethpm.update({'typeName': attr['typeName']})
                ethpm.update({'state': attr['state']})
        return ethpm

    def get_interface_eth_portchunnel_details(self, **kwargs):
        # Sprawdza czy interfejs eth należy do port-chunnel oraz pobiera dane port-chunnela
        pod = kwargs['pod']
        node_id = kwargs['node_id']
        slot = kwargs['slot']
        port_id = kwargs['port_id']
        port = slot+'/'+port_id
        pc={}

        pc_name = None
        url = ('/api/mo/topology/pod-'+pod+'/node-'+node_id+'/sys/phys-[eth'+port+'].json?query-target=subtree'
                     '&target-subtree-class=l1RtMbrIfs')
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        l1RtMbrIfs = self._get_query(url, error_message)
        if l1RtMbrIfs is False:
            self.logging.warning(error_message)
            return None
        else:
            pc={}
            pc_name = None

            if l1RtMbrIfs['totalCount'] != '0':
                attr = l1RtMbrIfs['imdata'][0]['l1RtMbrIfs']['attributes']
                # pc.update({'tCl': attr['tCl']})
                pc.update({'tSKey': attr['tSKey']})
                portchannel = InterfaceCollector(self.session, self.logging, self.bcolors)
                portchannel.populate_port_channels(node_id, pc['tSKey'])
                pc_name = portchannel._port_channels[0]['pcAggrIf']['attributes']['name']
                pc.update({'name': pc_name})
        return pc

    def get_interface_acc_config(self, **kwargs):
        # Sprawdza konfigurację acc policy dla interejsu
        pod = kwargs['pod']
        node_id = kwargs['node_id']
        slot = kwargs['slot']
        port_id = kwargs['port_id']
        port = slot+'/'+port_id
        inf_acc_conf ={}

        # Pobierz node name
        url = ('/api/node/class/fabricNode.json?query-target-filter=and(eq(fabricNode.id,"'+node_id+'"))')
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        node = self._get_query(url, error_message)

        # sprawdź czy node istnieje i czy jest aktywny
        if not node:
            self.logging.warning(error_message)
            return None
        elif node['imdata'][0]["fabricNode"]["attributes"]["fabricSt"] != "active":
            self.logging.warning('Node {} is not active'.format(node_id))
            return None

        node_name = node['imdata'][0]["fabricNode"]["attributes"]["name"]
        self.logging.info('Node name: {}'.format(node_name))

        # ACCESS POLICICIES
        url = ('/api/node/class/infraHPortS.json?'
                      'query-target-filter=and(wcard(infraHPortS.dn,"'+node_name+'"),'
                      'eq(infraHPortS.name,"eth'+slot+'_'+port_id+'"))'
                      '&rsp-subtree-include=relations'
                      )
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        infAccPol = self._get_query(url, error_message)

        if infAccPol:
            for acc_pol in infAccPol['imdata']:
                # self.logging.warning(acc_pol)
                for key in acc_pol.keys():
                    if (key == 'infraAccPortGrp') or (key == 'infraAccBndlGrp'):
                        inf_acc_conf.update({'AccPortGrp': acc_pol[key]['attributes']['name']})
                    elif key == 'infraHPortS':
                        inf_acc_conf.update({'AccDescr': acc_pol[key]['attributes']['descr']})

        else:
            self.logging.warning(error_message)
            self.logging.warning(infAccPol)
            return None

        return inf_acc_conf

    def get_interface_epg_config(self, **kwargs):
        # Sprawdza konfigurację epg dla interejsu
        pod = kwargs['pod']
        node_id = kwargs['node_id']
        slot = kwargs['slot']
        port_id = kwargs['port_id']
        port = slot+'/'+port_id
        pc_name = kwargs['pc_name']
        inf_conf ={}
        inf_conf_list = []

        if pc_name:
            self.logging.info('port w portchannelu '+pc_name)
            url = ('/api/class/fvRsPathAtt.json?query-target-filter=wcard(fvRsPathAtt.dn,"/pathep-\['+pc_name+'\]")')

        else:
            self.logging.info('Port nie należy do portchunnel')
            url = ('/api/class/fvRsPathAtt.json?query-target-filter=wcard(fvRsPathAtt.dn,"paths-'+node_id+'/pathep-\[eth'+port+'\]")')

        error_message = 'Could not collect APIC data for switch %s.' % node_id
        inf_conf1 = self._get_query(url, error_message)
        if inf_conf1 is False:
            self.logging.warning(error_message)
            return None

        if inf_conf1:
            try:
                self.logging.debug(inf_conf1['imdata'])
                for conf in inf_conf1['imdata']:
                    inf_conf = {}
                    attr = conf['fvRsPathAtt']['attributes']
                    inf_conf.update({'encap': attr['encap']})
                    modTs_date = time.strptime(attr['modTs'][:19], "%Y-%m-%dT%H:%M:%S")
                    inf_conf.update({'modTs': time.strftime("%Y-%m-%d %H:%M:%S", modTs_date)})
                    # inf_conf.update({'state': attr['state']})
                    dn = attr['dn']
                    # reg=re.match(r"^uni/tn-([a-zA-Z]+)/ap-([a-zA-Z0-9_-]+)/epg-([a-zA-Z0-9_-]+)", dn)
                    reg=re.match(r"uni.tn-([a-zA-Z0-9]+).ap-([a-zA-Z0-9_-]+).epg-([a-zA-Z0-9_-]+)", dn)
                    inf_conf.update({'tn': reg.group(1)})
                    inf_conf.update({'ap': reg.group(2)})
                    inf_conf.update({'epg': reg.group(3)})

                    # Dodaj inf_conf do listy
                    inf_conf_list.append(inf_conf)

            except:
                self.logging.warning('Nieznany błąd w konfig EPG')
                self.logging.warning(inf_conf1['imdata'])
                return None
        return inf_conf_list

    def sh_interface_detail(self, if_name=None):
        # Nazwa interfejsu składa się z interface_type, pod, node, module, port (eth 1/101/1/1)
        if if_name == None:
            self.logging.WARING(self.bcolors.WARNING +'Brak nazwy interfejsu')
            return ""

        # Wyodrębnij dane portu
        try:
            # reg = re.match(r"^eth\s(\d).(\d{3}).(.{3,5})$", if_name)
            reg = re.match(r"^eth\s(\d).(\d{3}).(\d).(\d{1,2})$", if_name)
            self.logging.info('pod ' + reg.group(1))
            pod = reg.group(1)
            self.logging.info('leaf ' + reg.group(2))
            node_id = reg.group(2)
            self.logging.info('port ' + reg.group(3))
            slot = reg.group(3)
            self.logging.info('port ' + reg.group(4))
            port_id = reg.group(4)
            port = slot+'/'+port_id
        except:
            self.logging.error("Błąd podczas odczytu wyrażenia regularnego dla if_name: "+if_name)
            return ''

        ###################################################
        #          Parametry fizyczne poru                #
        ###################################################

        phys = self.get_interface_phys_detail(pod=pod, node_id=node_id, slot=slot, port_id=port_id)
        if phys:
            print ("\nPhysical detalis")
            for keys, values in phys.items():
                print("     {:15s} :    {}".format(keys, values))

        ###################################################
        #                 SFP MEDIA                       #
        ###################################################

        ethpm = self.get_interface_media(pod=pod, node_id=node_id, slot=slot, port_id=port_id)
        if ethpm:
            print ("\nInterface media:")
            for keys, values in ethpm.items():
                print("     {:15s} :    {}".format(keys, values))

        ###################################################
        #         Konfiguracja port-chunnel               #
        ###################################################

        pc = self.get_interface_eth_portchunnel_details(pod=pod, node_id=node_id, slot=slot, port_id=port_id)
        pc_name = None
        if pc:
            print ("\nPort-channel")
            for keys, values in pc.items():
                print("     {:15s} :    {}".format(keys, values))
            pc_name = pc['name']

        ###################################################
        #         Konfiguracja ACC Policy                 #
        ###################################################
        inf_acc_conf = self.get_interface_acc_config(pod=pod, node_id=node_id, slot=slot, port_id=port_id)
        if inf_acc_conf:
            print ("\nACC Config")
            for keys, values in inf_acc_conf.items():
                print("     {:15s} :    {}".format(keys, values))

        ###################################################
        #               Konfiguracja EPG                  #
        ###################################################
        inf_conf = self.get_interface_epg_config(pod=pod, node_id=node_id, slot=slot, port_id=port_id, pc_name=pc_name)
        if inf_conf:
            print ("\nEPG Config")
            i = len(inf_conf)
            self.logging.debug(inf_conf)
            for epg_conf in inf_conf:
                for keys, values in epg_conf.items():
                    print("     {:15s} :    {}".format(keys, values))
                if i > 1:
                    print ('     ------------------------------------------------')
                    i = i-1

    def test(self, if_name=None):
        #wyłączenie testu:
        # return None

        # Nazwa interfejsu składa się z interface_type, pod, node, module, port (eth 1/101/1/1)
        if if_name == None:
            print ('Brak nazwy interfejsu')
            self.logging.WARING(self.bcolors.WARNING +'Brak nazwy interfejsu')
            return ""

        reg = re.match(r"^eth\s(\d).(\d{3}).(\d).(\d{1,2})$", if_name)
        self.logging.info('pod ' + reg.group(1))
        pod = reg.group(1)
        self.logging.info('leaf ' + reg.group(2))
        node_id = reg.group(2)
        self.logging.info('port ' + reg.group(3))
        slot = reg.group(3)
        self.logging.info('port ' + reg.group(4))
        port_id = reg.group(4)
        port = slot+'/'+port_id

        # Pobierz node name
        url = ('/api/node/class/fabricNode.json?query-target-filter=and(eq(fabricNode.id,"'+node_id+'"))')
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        node = self._get_query(url, error_message)

        # sprawdź czy node istnieje i czy jest aktywny
        if not node:
            self.logging.warning(error_message)
            return None
        elif node['imdata'][0]["fabricNode"]["attributes"]["fabricSt"] != "active":
            self.logging.warning('Node {} is not active'.format(node_id))
            return None

        node_name = node['imdata'][0]["fabricNode"]["attributes"]["name"]
        self.logging.info('Node name: {}'.format(node_name))

        # ACCESS POLICICIES
        url = ('/api/node/class/infraHPortS.json?'
                      'query-target-filter=and(wcard(infraHPortS.dn,"'+node_name+'"),'
                      'eq(infraHPortS.name,"eth'+slot+'_'+port_id+'"))'
                      '&rsp-subtree-include=relations'
                      )
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        infAccPol = self._get_query(url, error_message)

        if infAccPol:
            for k in infAccPol['imdata']:
                if 'infraAccPortGrp' in k.keys():
                    print k['infraAccPortGrp']['attributes']['name']
                    print k['infraAccPortGrp']['attributes']['nameAlias']





        # print(json.dumps(infraHPortS, indent=4, sort_keys=True))

        return None

    def interface_description_database(self, node, update=False, init=False, tuple=None):
        """
        Show the interface description
        Wyszukiwanie interfejsów na podstawie description
        zapisanych w lokalnej bazie danych w celu szybszego przeszukiwania
        :return: result
        """
        db_file = 'Database/interfaces_'+node+'.db'
        con = None
        try:
            con = sqlite3.connect(db_file)
        except:
            self.logging.warning("Nie mogę utworzyć / odczytać bazy danych dla noda "+node)
            return ''

        if not update:
            # SELECT all data from descriptions TABLE
            # con = sqlite3.connect(db_file)
            try:
                with con:
                    cur = con.cursor()
                    # cur.execute("SELECT * FROM descriptions WHERE description LIKE '%"+name+"%' ;")
                    cur.execute("SELECT * FROM descriptions")
                    rows = cur.fetchall()

                    return rows
            except sqlite3.Error as e:
                if con:
                    con.rollback()
                self.logging.warning("Error {}:".format(e))
            finally:
                if con:
                    con.close()
        else:
            try:
                # Connect and create database if not exist
                # con = sqlite3.connect(db)
                cur = con.cursor()

                if init:
                    # Drop table if exist and create new one
                    cur.executescript("""
                        DROP TABLE IF EXISTS descriptions;
                        CREATE TABLE IF NOT EXISTS descriptions(leaf TEXT, port TEXT, type TEXT, speed TEXT, description TEXT);
                        """)
                else:
                    cur.executescript("""
                        CREATE TABLE IF NOT EXISTS descriptions(leaf TEXT, port TEXT, type TEXT, speed TEXT, description TEXT);
                        """)
                    # get data from apic
                    cur.execute("INSERT INTO descriptions VALUES ('{}','{}','{}','{}','{}');".format(tuple[0],tuple[1],tuple[2],tuple[3],tuple[4]))
                    con.commit()
            except sqlite3.Error as e:
                if con:
                    con.rollback()
                self.logging.warning("Error {}:".format(e))

            finally:
                if con:
                    con.close()

    def search_interface_by_description(self, name=None, online=True, apic_intf_class='l1PhysIf',node_id=None,  specific_interface=None):
        """
        Show the interface description
        Wyszukiwanie interfejsów na podstawie description
        :return: result
        """
        nodes = self.get_node_ids()

        # setup toolbar
        toolbar_width = len(nodes)
        result = []
        description =''

        if online:
            print ("\nBuduję bazę danych online na podstawie wysztkich leafów...")
            sys.stdout.write("[%s]" % (" " * toolbar_width))
            sys.stdout.flush()
            sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['


            for node in nodes:
                # Initialize TABLE in database
                self.interface_description_database(node, True, True)
                data = self.show_interface_description(node, apic_intf_class, None, False)
                if data:
                    for inf in data:
                        # send in local database
                        self.interface_description_database(node, True, False, inf)
                        description = inf[len(data[0])-1]
                        description = str(description)
                        # self.logging.info("Szukam {} w {}".format(name, description))
                        if description.find(name) >= 0:
                            result.append(inf)
                # progress bar
                sys.stdout.write("#")
                sys.stdout.flush()


            sys.stdout.write("]\n") # this ends the progress bar
        else:
            for node in nodes:
                try:
                    data = self.interface_description_database(node, False, False, None)
                    for d in data:
                        description = d[-1]
                        # self.logging.info(description)
                        if description.find(name) >= 0:
                            result.append(d)
                except:
                    self.logging.warning("")

        return result

    def show_interface_description(self, node_id, apic_intf_class='l1PhysIf', specific_interface=None, printable=True):
        """
        Show the interface description
        :param node_ids: nodes names
        :param specific_interface: specific interface
        :return: data
        """
        self.logging.debug("node_id {}, apic_intf_class {}, specific_interface {}, printable {}".format(node_id, apic_intf_class, specific_interface, printable))
        if printable:
            print('Switch:', node_id)
        # for node_id in node_ids:
        query_url = ('/api/mo/topology/pod-1/node-%s.json?query-target=subtree'
                     '&target-subtree-class=%s' % (node_id, apic_intf_class))
        if specific_interface is not None:
            query_url += '&query-target-filter=eq(%s.id,"%s")' % (apic_intf_class,
                                                                  specific_interface)
        resp = self.session.get(query_url)
        if not resp.ok:
            self.logging.warning(self.bcolors.WARNING +'Could not collect APIC data for switch %s.' % node_id)
            print('Could not collect APIC data for switch %s.' % node_id)
            print(resp.text)
            return
        data = []
        headers = []
        self.logging.info('Szukam description dla noda %s.' % node_id)
        for obj in resp.json()['imdata']:
            obj_attr = obj[apic_intf_class]['attributes']
            if obj_attr['descr'] == '':
                description = '--'
            else:
                description = obj_attr['descr']
            if 'speed' in obj_attr:
                data.append((node_id, obj_attr['id'], 'eth', obj_attr['speed'], description))
                headers = ["Node", "Port", "Type", "Speed", "Description"]
            else:
                data.append((node_id, obj_attr['id'], description))
                headers = ["Node", "Interfaces", "Description"]
        if printable and len(headers) and len(data):
            print(tabulate(data, headers=headers, tablefmt="github"))
            print('\n')

        return data

    def get_node_ids(self, switch=None):
        """
        Get the list of node ids from the command line arguments.
        If none, get all of the node ids

        :return: List of strings containing node ids
        """
        if switch is not None:
            names = [switch]
        else:
            names = []
            query_url = ('/api/node/class/fabricNode.json?'
                         'query-target-filter=eq(fabricNode.role,"leaf")')
            resp = self.session.get(query_url)
            if not resp.ok:
                print('Could not get switch list from APIC.')
                return
            nodes = resp.json()['imdata']
            for node in nodes:
                names.append(str(node['fabricNode']['attributes']['id']))
        return names


class INTERAFES_STATS:

    def __init__(self, session, logging, bcolors):
        # session to APIC
        self.session = session
        # get Intercaes
        self.interfaces = aci.Interface.get(self.session)
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def show_stats_short(self, interfaces, granularity='5min', epoch=0, nonzero=True):
        """
        show stats short routine

        :param args: command line arguments
        :param interfaces: list of interfaces
        :return: None
        """
        # setup template and display header information
        template = "{0:17} {1:12} {2:12} {3:16} {4:16} {5:16} {6:16}"
        print('Granularity: ' + str(granularity) + ' Epoch:' + str(epoch))
        print(template.format("   INTERFACE  ", "TOT RX PACKETS", "TOT TX PACKETS", "RX PKTs/Sec", "TX PKTs/Sec", "RX BYTES/Sec", "TX BYTES/Sec"))
        print(template.format("--------------", "------------ ", "------------ ", "---------------",
                              "---------------", "---------------", "---------------"))
        template = "{0:17} {1:12,} {2:12,} {3:16,.2f} {4:16,.2f} {5:16,.2f} {6:16,.2f}"

        for interface in sorted(interfaces, key=attrgetter('if_name')):
            interface.stats.get()

            rec = []
            allzero = True
            for (counter_family, counter_name) in [('ingrTotal', 'pktsAvg'), ('egrTotal', 'pktsAvg'),
                                                   ('ingrTotal', 'pktsRateAvg'), ('egrTotal', 'pktsRateAvg'),
                                                   ('ingrTotal', 'bytesRateAvg'), ('egrTotal', 'bytesRateAvg')]:

                rec.append(interface.stats.retrieve(counter_family, granularity, epoch, counter_name))
                if interface.stats.retrieve(counter_family, granularity, epoch, counter_name) != 0:
                    allzero = False

            if (nonzero and not allzero) or not nonzero:
                print(template.format(interface.name, *rec))

    def show_stats_long(self, interfaces, granularity='5min', epoch=0):
        """
        show stats long routine

        :param args: command line arguments
        :param interfaces: list of interfaces
        :return: None
        """
        print('Interface {0}/{1}/{2}/{3}  Granularity:{4} Epoch:{5}'.format(interfaces[0].pod,
                                                                            interfaces[0].node,
                                                                            interfaces[0].module,
                                                                            interfaces[0].port,
                                                                            granularity,
                                                                            epoch))
        stats = interfaces[0].stats.get()
        for stats_family in sorted(stats):
            print(stats_family)
            if granularity in stats[stats_family]:
                if epoch in stats[stats_family][granularity]:
                    for counter in sorted(stats[stats_family][granularity][epoch]):
                        print('    {0:>16}: {1}'.format(counter,
                                                        stats[stats_family][granularity][epoch][counter]))

    def get_stats(self, interface=None):
            # Download all of the interfaces and get their stats
            # and display the stats
            if interface:
                interface = interface
                if 'eth ' in interface:
                    interface = interface[4:]
                (pod, node, module, port) = interface.split('/')
                interfaces = aci.Interface.get(self.session, pod, node, module, port)
                self.show_stats_short(interfaces)
            else:
                # interfaces = aci.Interface.get(self.session)
                print('% Incomplete command.')
                self.logging.error('Nie podano interfejsu')


class InterfaceCollector(object):

    def __init__(self, session, logging=None, bcolors=None):
        # Login to APIC
        self._apic = session
        self._interfaces = []
        self._port_channels = []
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def _get_query(self, query_url, error_msg):
        resp = self._apic.get(query_url)
        if not resp.ok:
            print(error_msg)
            print(resp.text)
            return []

        if resp.json()['totalCount'] == '0':
            self.logging.warning ('% Wystąpił błąd. Sprawdź dane i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return False

        elif resp.json()['imdata'][0].keys()[0] == 'error':
            self.logging.warning ('% Wystąpił błąd. Sprawdź dane i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return False

        return resp.json()['imdata']

    def populate_port_channels(self, node_id, intf_id=None):
        pod = node_id[:1]
        query_url = ('/api/mo/topology/pod-'+pod+'/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=pcAggrIf&rsp-subtree=children&'
                     'rsp-subtree-class=ethpmAggrIf,pcRsMbrIfs' % node_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        try:
            port_channels = self._get_query(query_url, error_message)
            if intf_id is None:
                self._port_channels = port_channels
            else:
                self._port_channels = []
                for port_channel in port_channels:
                    for if_type in port_channel:
                        if port_channel[if_type]['attributes']['id'] == intf_id:
                            self._port_channels.append(port_channel)
        except:
            print (error_message)

    def populate_interfaces(self, node_id):
        pod = node_id[:1]
        query_url = ('/api/mo/topology/pod-'+pod+'/node-%s/sys.json?query-target=subtree'
                     '&target-subtree-class=l1PhysIf&rsp-subtree=children&'
                     'rsp-subtree-class=pcAggrMbrIf' % node_id)
        error_message = 'Could not collect APIC data for switch %s.' % node_id
        self._interfaces = self._get_query(query_url, error_message)

    def get_node_ids(self, node_id):
        """
        Get the list of node ids from the command line arguments.
        If none, get all of the node ids
        :param args: Command line arguments
        :return: List of strings containing node ids
        """
        if node_id is not None:
            names = [node_id]
        else:
            names = []
            query_url = ('/api/node/class/fabricNode.json?'
                         'query-target-filter=eq(fabricNode.role,"leaf")')
            error_message = 'Could not get switch list from APIC.'
            nodes = self._get_query(query_url, error_message)
            for node in nodes:
                names.append(str(node['fabricNode']['attributes']['id']))
        return names

    def _get_member_extension(self, port_channel):
        resp = ''
        # print(port_channel)
        # print(port_channel) -> wynik przykładowego po w portchannel_tmp_dict_output
        for child in port_channel['pcAggrIf']['children']:
            if 'pcRsMbrIfs' in child:
                for interface in self._interfaces:
                    # print (interface)
                    if child['pcRsMbrIfs']['attributes']['tDn'] == interface['l1PhysIf']['attributes']['dn']:
                        oper_attr = interface['l1PhysIf']['children'][0]['pcAggrMbrIf']['attributes']
                        if oper_attr['operSt'] == 'module-removed':
                            resp = '(r)'
                        elif oper_attr['operSt'] == 'up':
                            resp = '(P)'
                        elif oper_attr['channelingSt'] == 'individual':
                            resp = "(I)"
                        elif oper_attr['channelingSt'] == 'suspended':
                            resp = "(s)"
                        elif oper_attr['channelingSt'] == 'hot-standby':
                            resp = "(H)"
                        else:
                            resp = "(D)"
                    if resp != '':
                        break
        return resp

    def show_summary(self, node=None, intf_id=None):
        """
        show port-channel summary

        :param node: String containing the specific switch id. If none, all switches are used
        :param intf_id: String containing the specific interface id. If none, all interfaces are used
        :return: None
        """
        members = None
        self.logging.info("Node {} intf_id {}".format(node, intf_id))

        for node_id in self.get_node_ids(node):
            self.populate_interfaces(node_id)
            self.populate_port_channels(node_id, intf_id)
            if not len(self._port_channels):
                continue
            print("Switch: %s" % str(node_id))
            print("Flags:  D - Down        P - Up in port-channel (members)")
            print("        I - Individual  H - Hot-standby (LACP only)")
            print("        s - Suspended   r - Module-removed")
            print("        S - Switched    R - Routed")
            print("        U - Up (port-channel)")
            print("        M - Not in use. Min-links not met")
            print("        F - Configuration failed")
            data = []
            for interface in self._port_channels:
                intf_attr = interface['pcAggrIf']['attributes']
                name = intf_attr['id']
                acc_name = intf_attr['name']
                if_speed = intf_attr['speed']
                if intf_attr['layer'] == 'Layer2':
                    name += "(S"
                else:
                    name += "(R"

                for child in interface['pcAggrIf']['children']:
                    if 'ethpmAggrIf' in child:
                        oper_attr = child['ethpmAggrIf']['attributes']
                        if oper_attr['operSt'] == 'up':
                            name += "U)"
                        elif intf_attr['suspMinlinks'] == 'yes':
                            name += "M)"
                        else:
                            name += "D)"
                        members = oper_attr['activeMbrs']
                        while ',unspecified,' in members:
                            members = members.replace(',unspecified,', ',')
                        members = members.replace(',unspecified', '')

                members += self._get_member_extension(interface)
                protocol = 'none'
                if intf_attr['pcMode'] in ['active', 'passive', 'mac-pin']:
                    protocol = 'lacp'
                data.append((int(intf_attr['id'][2:]), name, acc_name, if_speed, 'eth', protocol, members))
            data.sort(key=lambda tup: tup[0])
            # headers = ['Group', 'Port channel', 'Type', 'Protocol', 'Member Ports']
            # print(tabulate(data, headers=headers))
            print ('\n')
            print tabulate(data, headers=['Group', 'Port channel', 'Name', 'Speed', 'Type', 'Protocol', 'Member Ports'], tablefmt="github")

    def _get_vpc_pairs(self):
        self.logging.info('_get_vpc_pairs')
        query_url = ('/api/node/mo/uni/fabric/protpol.json?query-target=children')
        error_message = 'Could not collect APIC data.'
        vpc_pairs_raw = self._get_query(query_url, error_message)

        if vpc_pairs_raw:
            vpc_pairs = []
            self.logging.debug(vpc_pairs_raw)
            for vpc_pair in vpc_pairs_raw:
                vpc_pairs.append((vpc_pair['fabricExplicitGEp']['attributes']['dn'], vpc_pair['fabricExplicitGEp']['attributes']['name']))

            return vpc_pairs
        else:
            return None

    def test(self):
        return None
        print (self._get_vpc_pairs())
        return ''
