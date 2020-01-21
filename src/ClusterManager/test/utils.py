#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.parse
import json
import argparse
import logging
import datetime
import time

import requests

logger = logging.getLogger(__file__)

def post_regular_job(rest_url, email, uid, vc, cmd):
    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "gpuType": "P40",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "DeepScale1.0-Regular",
        "jobtrainingtype": "RegularJob",
        "preemptionAllowed": "False",
        "image": "indexserveregistry.azurecr.io/deepscale:1.0.post0",
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": True,
        "env": [],
        "hostNetwork": False,
        "isPrivileged": False,
        "resourcegpu": 0,
        "cpulimit": 1,
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url, data=json.dumps(args)) # do not handle exception here
    jid = resp.json()["jobId"]
    logger.info("job %s created", jid)
    return jid

def post_distributed_job(rest_url, email, uid, vc, cmd):
    args = {
        "userName": email,
        "userId": uid,
        "jobType": "training",
        "gpuType": "P40",
        "vcName": vc,
        "containerUserId": 0,
        "jobName": "DeepScale1.0-Distributed",
        "jobtrainingtype": "PSDistJob",
        "preemptionAllowed": "False",
        "image": "indexserveregistry.azurecr.io/deepscale:1.0.post0",
        "cmd": cmd,
        "workPath": "./",
        "enableworkpath": True,
        "dataPath": "./",
        "enabledatapath": True,
        "jobPath": "",
        "enablejobpath": False,
        "env": [],
        "hostNetwork": True,
        "isPrivileged": True,
        "numps": 1,
        "resourcegpu": 0,
        "numpsworker": 1
    }
    url = urllib.parse.urljoin(rest_url, "/PostJob")
    resp = requests.post(url, data=json.dumps(args)) # do not handle exception here
    jid = resp.json()["jobId"]
    logger.info("job %s created", jid)
    return jid

def get_job_status(rest_url, job_id):
    args = urllib.parse.urlencode({
        "jobId": job_id,
        })
    url = urllib.parse.urljoin(rest_url, "/GetJobStatus") + "?" + args
    resp = requests.get(url)
    return resp.json()

def get_job_detail(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
        })
    url = urllib.parse.urljoin(rest_url, "/GetJobDetail") + "?" + args
    resp = requests.get(url)
    return resp.json()

def kill_job(rest_url, email, job_id):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": job_id,
        })
    url = urllib.parse.urljoin(rest_url, "/KillJob") + "?" + args
    resp = requests.get(url)
    return resp.json()

class run_job(object):
    def __init__(self, rest_url, job_type, email, uid, vc, cmd):
        self.rest_url = rest_url
        self.job_type = job_type
        self.email = email
        self.uid = uid
        self.vc = vc
        self.cmd = cmd
        self.jid = None

    def __enter__(self):
        if self.job_type == "regular":
            self.jid = post_regular_job(self.rest_url, self.email, self.uid, self.vc, self.cmd)
        elif self.job_type == "distributed":
            self.jid = post_distributed_job(self.rest_url, self.email, self.uid, self.vc, self.cmd)
        return self

    def __exit__(self, type, value, traceback):
        try:
            resp = kill_job(self.rest_url, self.email, self.jid)
            logger.info("killed job %s", self.jid)
        except Exception:
            logger.exception("failed to kill job %s", self.jid)

def block_until_running(rest_url, jid, timeout=60):
    start = datetime.datetime.now()
    delta = datetime.timedelta(seconds=timeout)
    waiting_state = {"unapproved", "queued", "scheduling"}

    while True:
        status = get_job_status(rest_url, jid)["jobStatus"]

        if status in waiting_state:
            logger.debug("waiting status in %s", status)
            if datetime.datetime.now() - start < delta:
                time.sleep(1)
            else:
                raise RuntimeError("Job stays in %s for more than %d seconds" % (status, timeout))
        elif status == "running":
            logger.info("spent %s in waiting job running", datetime.datetime.now() - start)
            return status
        else:
            raise RuntimeError("Got unexpected job status %s for job %s" % (status, jid))

def get_job_log(rest_url, email, jid):
    args = urllib.parse.urlencode({
        "userName": email,
        "jobId": jid,
        })
    url = urllib.parse.urljoin(rest_url, "/GetJobLog") + "?" + args
    resp = requests.get(url)
    return resp.json()