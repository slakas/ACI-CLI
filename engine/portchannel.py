#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
This application replicates the switch CLI command 'show port-channel summary'
It largely uses raw queries to the APIC API
"""

from tabulate import tabulate


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
