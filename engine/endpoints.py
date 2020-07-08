#!/usr/bin/env python
# -*- encoding: utf-8 -*-
### ENDPOINTS MODULE

import engine.acitoolkit.acitoolkit as aci
from engine.acitoolkit.aciTable import Table
import ipaddress
from tabulate import tabulate
from operator import attrgetter, itemgetter
import re

data = []

class ENDPOINTS():
    """docstring for Endpoint."""

    def __init__(self, session, tenant=None, logging=None, bcolors=None):
        self.endpoints_data = []
        # session to APIC
        self.session = session
        self.tenant = tenant
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors


    @staticmethod
    def get_table(endpoints, title=''):
        """
        Will create table of taboo information for a given tenant

        :param title:
        :param endpoints:
        """

        result = []
        headers = ['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
                   'Encap']

        data = []
        for endpoint in sorted(endpoints, key=attrgetter('name')):
            epg = endpoint.get_parent()
            bd = 'Not Set'
            context = 'Not Set'
            if epg.has_bd():
                bd = epg.get_bd().name
                if epg.get_bd().has_context():
                    context = epg.get_bd().get_context().name

            data.append([
                endpoint.get_parent().get_parent().get_parent().name,
                context,
                bd,
                endpoint.get_parent().get_parent().name,
                endpoint.get_parent().name,
                endpoint.name,
                endpoint.mac,
                endpoint.ip,
                endpoint.if_name,
                endpoint.encap
            ])
        data = sorted(data, key=itemgetter(1, 2, 3, 4))

        # print tabulate(data, headers=['Tenant', 'Context', 'Bridge Domain', 'App Profile', 'EPG', 'Name', 'MAC', 'IP', 'Interface',
        #            'Encap'])
        return data

    def get_endpoints(self, **kwargs):


        for key, value in kwargs.items():
            # find addres in endpoints
            if key == 'ip' and unicode(value) == unicode(ep.ip):
                # # Download all of the interfaces
                # endpoints = aci.Endpoint.get(self.session)
                # # add result to list
                # self.endpoints_data = self.get_table(endpoints)
                print ('Funkcja w trakcie budowy')

            elif key == 'mac':
                # Download specific endpoint
                try:
                    endpoint = aci.Endpoint.get(self.session, value)
                    self.endpoints_data = self.get_table(endpoint)
                except:
                    self.logging.error("Brak wyników dla: "+value)

            elif key == 'epg':
                try:
                    # TenantRadek1:AP1Rad:App1
                    epg_path = re.match(r"^(.+):(.+):(.+)$", value)
                    self.logging.info(epg_path.group(1))
                    self.logging.info(epg_path.group(2))
                    self.logging.info(epg_path.group(3))
                    # def get_all_by_epg(cls, session, tenant_name, app_name, epg_name, with_interface_attachments=True):
                    endpoint = aci.Endpoint.get_all_by_epg(self.session, epg_path.group(1), epg_path.group(2), epg_path.group(3), False)
                    self.endpoints_data = self.get_table(endpoint)
                    return self.get_table(endpoint)
                except:
                    self.logging.error("Brak wyników dla: "+value)


        # for ep in endpoints:
        #     epg = ep.get_parent()
        #     app_profile = epg.get_parent()
        #     tenant = app_profile.get_parent()
        #
        #     if self.tenant is not None:
        #         if self.tenant.name != tenant.name:
        #             continue
        #
        #     for key, value in kwargs.items():
        #         # find addres in endpoints
        #         if key == 'ip' and unicode(value) == unicode(ep.ip):
        #             #     # add result to list
        #             self.endpoints_data.append((ep.mac, ep.ip, ep.if_name, ep.encap,
        #                      tenant.name, app_profile.name, epg.name))
        #         elif key == 'mac' and unicode(value) == unicode(ep.mac):
        #             self.endpoints_data.append((ep.mac, ep.ip, ep.if_name, ep.encap,
        #                      tenant.name, app_profile.name, epg.name))
        #         elif key == 'pod':
        #             self.logging.info("ifname {} if_dn {} timestamp {}".format(ep.if_name, ep.if_dn, ep.timestamp))
                # if unicode(value) == unicode(ep.mac) or unicode(value) == unicode(ep.ip):
                #     # add result to list
                #     self.endpoints_data.append((ep.mac, ep.ip, ep.if_name, ep.encap,
                #              tenant.name, app_profile.name, epg.name))

    def get_all_endpoints(self):
        endpoints = aci.Endpoint.get(self.session)
        for ep in endpoints:
            epg = ep.get_parent()
            app_profile = epg.get_parent()
            tenant = app_profile.get_parent()

            if self.tenant is not None:
                if self.tenant.name != tenant.name:
                    continue
            # add result to list
            self.endpoints_data.append((ep.mac, ep.ip, ep.if_name, ep.encap,
                     tenant.name, app_profile.name, epg.name))

    def addres(self, **kwargs):
        pod = None
        addr= None

        self.logging.info(kwargs)

        # if addr is null get all endpoints

        for key, value in kwargs.items():
            if key == 'pod':
                pod = value
            elif key == 'addr':
                addr = value


        if not addr:
            # Opcja wyszukaj wszystkie endpointy ograniczona do podów
            # self.logging.info("pod {}".format(pod))
            self.get_endpoints(pod=pod)
        else:
            self.logging.info(addr)
            # check addr ip or MAC
            try:
                # if addres is IPv4 private
                if ipaddress.ip_address(unicode(addr)).is_private is True:
                    self.logging.info(self.bcolors.INFO + "Szukam endpointów ")
                    self.get_endpoints(ip=unicode(addr))
            except:
                # if addr is MAC
                p = re.compile(ur'(?:[0-9a-fA-F]:?){12}')
                mac_addr = re.findall(p, unicode(addr))
                if mac_addr:
                    # print (result)
                    self.get_endpoints(mac=mac_addr[0])
                else:
                    print ("Podano bledny ciag znakow")
                    print(":(")

        # print tabulate(self.endpoints_data, headers=["MACADDRESS", "IPADDRESS", "INTERFACE",
        #                               "ENCAP", "TENANT", "APP PROFILE", "EPG"])
