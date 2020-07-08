#!/usr/bin/env python
# -*- encoding: utf-8 -*-


from acitoolkit import Faults
from tabulate import tabulate
import time
from datetime import date as datetime
import json
import os

class ShowFaults():

    def __init__(self, session, tenant=None, domain=None, logging=None, bcolors=None):
        # session to APIC
        self.session = session
        self.tenant = tenant
        self.domain_name = domain
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def by_domain(self):
        faults_obj = Faults()
        fault_filter = None
        if self.domain_name is not None:
            fault_filter = {'domain': self.domain_name.split(',')}

        tenant_name = None
        if self.tenant is not None:
            tenant_name = self.tenant.name

        faults_obj.subscribe_faults(self.session, fault_filter)
        # while faults_obj.has_faults(session, fault_filter) or args.continuous:
        while faults_obj.has_faults(self.session, fault_filter):
            if faults_obj.has_faults(self.session, fault_filter):
                faults = faults_obj.get_faults(
                    self.session, fault_filter=fault_filter, tenant_name=tenant_name)
                if faults is not None:
                    for fault in faults:
                        if fault is not None:
                            print("---------------")
                            if fault.descr is not None:
                                print("     descr     : " + fault.descr)
                            else:
                                print("     descr     : " + "  ")
                            print("     dn        : " + fault.dn)
                            print("     rule      : " + fault.rule)
                            print("     severity  : " + fault.severity)
                            print("     type      : " + fault.type)
                            print("     domain    : " + fault.domain)

    def clear(self):
        self.session = None
        self.tenant = None
        self.domain_name = None


class AuditLog():
    """docstring for aci-show-faults-by-domain"""
    description = 'class that logs on to the APIC and displays AuditLogs'

    def __init__(self, session, tenant=None, logging=None, bcolors=None):
        # session to APIC
        self.session = session
        self.tenant = tenant
        # self.domain_name = domain
        #  logging engine
        self.logging = logging
        self.bcolors = bcolors

    def _get_query(self, query_url, error_msg):
        resp = self.session.get(query_url)
        if not resp.ok:
            print(error_msg)
            print(resp.text)
            return []
        # print yaml.dump(resp.json(), default_flow_style=False)
        # return resp.json()['imdata']
        return resp.json()

    def get_audit_logs(self, wizard_mode=True):

        query_url = ('/api/class/aaaModLR.json?')
        today = datetime.today()

        if wizard_mode is True:
            print('     Wyświetl audit logs ')
            created_from = raw_input('      od dnia [yyyy-mm-dd]: ')
            current_date = today.strftime("%Y-%m-%d")
            created_to = raw_input('      do dnia ['+current_date+']: ') or current_date
            # query_url += 'query-target-filter=and(ge(aaaModLR.created,"'+created_from+'"),le(aaaModLR.created,"'+created_to+'"))'
            query_url += 'query-target-filter=and(le(aaaModLR.created,"'+created_to+'"),ge(aaaModLR.created,"'+created_from+'"))'

        self.logging.debug(query_url)
        error_message = 'Could not get switch list from APIC.'
        resp = self._get_query(query_url, error_message)
        self.logging.debug(resp)

        if resp['totalCount'] == '0':
            print ('% Wystąpił błąd. Sprawdź wprowadzoną datę i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return ''

        elif resp['imdata'][0].keys()[0] == 'error':
            print ('% Wystąpił błąd. Sprawdź wprowadzoną datę i spróbuj jeszcze raz.')
            self.logging.warning(resp)
            return ''

        audit_logs = resp['imdata']
        headers = ['id', 'affected', 'descr', 'created', 'ind', 'user']
        values = []
        values_lists=[]
        rowIDs = 0

        filter = raw_input('\n      Filtrować wyniki? [T/N]: ')
        if filter.lower() == 't':
            username = raw_input('            użytkownik: ')
            affected = raw_input('            obiekt: ')
            for log in audit_logs:
                values_lists=[]
                log = log['aaaModLR']['attributes']
                if (username != '') and (affected!= ''):
                    if (log['user'].find(username) >= 0) and (log['affected'].find(affected) >= 0):
                        rowIDs += 1
                        values_lists.append(rowIDs)
                        for k in headers[1:]:
                            if k == 'created':
                                date = time.strptime(log[k][:19], "%Y-%m-%dT%H:%M:%S")
                                values_lists.append(time.strftime("%Y-%m-%d %H:%M:%S", date))
                            else:
                                values_lists.append(log[k])
                        values.append(list(values_lists))
                elif username != '':
                    if log['user'].find(username) >= 0:
                        rowIDs += 1
                        values_lists.append(rowIDs)
                        for k in headers[1:]:
                            if k == 'created':
                                date = time.strptime(log[k][:19], "%Y-%m-%dT%H:%M:%S")
                                values_lists.append(time.strftime("%Y-%m-%d %H:%M:%S", date))
                            else:
                                values_lists.append(log[k])
                        values.append(list(values_lists))
                elif affected != '':
                    if log['affected'].find(affected) >= 0:
                        rowIDs += 1
                        values_lists.append(rowIDs)
                        for k in headers[1:]:
                            if k == 'created':
                                date = time.strptime(log[k][:19], "%Y-%m-%dT%H:%M:%S")
                                values_lists.append(time.strftime("%Y-%m-%d %H:%M:%S", date))
                            else:
                                values_lists.append(log[k])
                        values.append(list(values_lists))

        else:
            for log in audit_logs:
                values_lists=[]
                log = log['aaaModLR']['attributes']
                rowIDs += 1
                values_lists.append(rowIDs)
                for k in headers[1:]:
                    if k == 'created':
                        date = time.strptime(log[k][:19], "%Y-%m-%dT%H:%M:%S")
                        values_lists.append(time.strftime("%Y-%m-%d %H:%M:%S", date))
                    else:
                        values_lists.append(log[k])
                values.append(list(values_lists))

        if rowIDs > 0:
            print ('\n')
            # sort results by date
            values = sorted(values, key=lambda log: log[3])
            # correct rowIDs
            new_rowID = 0
            for value in values:
                value[0] = new_rowID
                new_rowID += 1
            i = 0
            n = len(values)
            self.logging.info(n)
            if n > 40:
                while i < n:
                    os.system('clear')
                    print tabulate(values[i:i+40], headers)
                    print ('\n')
                    os.system("""bash -c 'read -s -n 1 -p "$(tput setaf 0)$(tput setab 7)Press any key to continue...$(tput sgr 0)"'""")
                    print ('\n')
                    i += 40
                    pass
                self.logging.info(i)
            else:
                print tabulate(values, headers)
            return values
        else:
            print ('\n')
            print ('Nie znaleziono')
            return ''
        # print(json.dumps(resp, indent=4, sort_keys=True))
