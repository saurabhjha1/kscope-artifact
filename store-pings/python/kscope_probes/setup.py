#!/usr/bin/env python
import os 
import sys
from runcmd import runcmd, Run_Cmd_Error
from pprint import pprint
import argparse
import socket
import re
import time
import multiprocessing
from functools import partial
from abortable_worker import abortable_worker
import copy
import shutil
"""
snx11000-MDT0000-mdc-ffff8803ea347400: active
snxtest-MDT0000-mdc-ffff8803f29e4800: active
"""
# TODO setstripe enable check and raise error on false
def __setstripe__(args):
		fname = args[0]
		ost = args[1]
		cmd = ["lfs", "setstripe"]
		opts = None
		args = ["-c", "1", "-i" + str(ost), fname]
		status = None
		output = None
		errput = None
		ret = None
		try:
			(output, errput, ret) = runcmd(cmd, opts, args)
		except Exception as e:
			print(e.code, e.reason)
		if ret == 0:
			status = True
			#if __checkstripe__([fname, ost]):
			#	status = True
		return status

def __checkstripe__(args):
		fname = args[0]
		ost = args[1]
		cmd = [ 'lfs', 'getstripe' ]
		opts = None
		args = [ fname ]
		ret = None
		( output, errput, ret ) = runcmd( cmd, opts, args )
		stripe_count = 0
		stripe_index = -1
		status = None
		if ret == 0:
			for line in output.decode('utf8').split('\n'):
				if "lmm_stripe_offset" in line:
					stripe_index = int(line.split(":")[1])
				if "lmm_stripe_count" in line:
					stripe_count = int(line.split(":")[1])
			if stripe_count == 1 and stripe_index == ost:
				status = True
		return status	

def __k_wrex__(args):
		fsname = args[0]
		ost_id = args[1]
		pb_id = args[2]
		ost_file = args[3]
		t_start = time.time()
		#if not os.path.isfile(ost_file):
		#	return (time.time(), fsname, ost_id, pb_id, 0, -1)
		try:
			cmd = ["dd"]
			opts = {"if":"/dev/zero", "of":ost_file, "bs":"4k", "oflag":"direct", "count":"1"}
			args = None
			ret = None
			(output, errput, ret) = runcmd(cmd, opts, args)
			if ret == 0:
				duration = errput.decode('utf8').split()[-4]
				return (t_start, fsname, ost_id, pb_id, duration, 0)
			else:
				t_end = time.time()
				return (t_start, fsname, ost_id, pb_id, t_end - t_start, -2)
			# dd if=/dev/zero of=./test bs=4k oflag=direct count=1 2>&1 | tail -1 | awk {'print $6'}
		except Exception as e:
			t_end = time.time()
			return  (t_start, fsname, ost_id, pb_id, t_end - t_start, str(e))

def __k_crwr__(args):
		fsname = args[0]
		ost_id = args[1]
		pb_id = args[2]
		ost_file = args[3]
		if os.path.isfile(ost_file):
			os.remove(ost_file)
		t_start = time.time()
		try:
			if ost_id != -1:
				__setstripe__([ost_file, ost_id])
			cmd = ["dd"]
			opts = {"if":"/dev/zero", "of":ost_file, "bs":"4k", "oflag":"direct", "count":"1"}
			args = None
			ret = None
			(output, errput, ret) = runcmd(cmd, opts, args)
			if ret == 0:
				duration = errput.decode('utf8').split()[-4]
				return (t_start, fsname, ost_id, pb_id, duration, 0) #TODO 
			else:	
				t_end = time.time()
				return (t_start, fsname, ost_id, pb_id, t_end - t_start, -2)
		except Exception as e:
			t_end = time.time()
			return (t_start, fsname, ost_id, pb_id, t_end - t_start, str(e))

def __k_rmex__(args):
		fsname = args[0]
		ost_id = args[1]
		pb_id = args[2]
		ost_file = args[3]
		
		if not os.path.exists(ost_file):
			return (t_start, fsname, ost_id, pb_id, 0, -2)
		t_start = time.time()
		try:
			os.remove(ost_file)
			t_end = time.time()
			return (t_start, fsname, ost_id, pb_id,  t_end - t_start, 0)
		except Exception as e:
			t_end = time.time()
			return (t_start, fsname, ost_id, pb_id, t_end - t_start, str(e))

def __k_ls__(args):
		fsname = args[0]
		ost_id = args[1]
		pb_id = args[2]
		wdir = args[3]
		t_start = time.time()
		try:
			k = os.listdir(wdir)
			t_end = time.time()
			return (t_start, fsname, ost_id, pb_id, t_end - t_start, 0)
		except Exception as e:
			t_end = time.time()
			return (t_start, fsname, ost_id, pb_id, t_end - t_start, str(e))


def __k_ost__(args):
	args_wrex = args[0]
	args_crwr = args[1]
	args_rmex = args[2]
	pb_t = []
	pb_t.append(__k_wrex__(args_wrex))
	pb_t.append(__k_crwr__(args_crwr))
	pb_t.append(__k_rmex__(args_rmex))
	return pb_t

def __k_mdt__(args):
	pb_t = []
	pb_t.append(__k_ls__(args))
	return pb_t


class	KSProbes:
	def __init__(self, threads, timeout, config_file):
		self.threads = int(threads)
		self.timeout = float(timeout)
		self.layout = {}
		self.hostname = socket.gethostname()
		self.db = []
		self.ost_tasks = []
		self.mdt_tasks = []
		with open(config_file, 'r') as ifh:
			for line in ifh:
				cols = line.rstrip().split(",")
				if len(cols)==4:
					fsname = cols[0]
					mdts = int(cols[1])
					osts = int(cols[2])
					wdir = cols[3]
					self.layout[fsname] = {"mdts": list(range(mdts)), "mdts_health": {}, "osts": list(range(osts)), "osts_health":{}, "wdir": wdir}
		self.__set_health__()
		
	def __set_health__(self):
		cmd = ["lfs", "check", "servers"]
		opts = None
		args = None
		ret = None
		(output, errput, ret) = runcmd(cmd, opts, args)
		if ret == 0 :
			for line in output.decode('utf8'):
				cols = line.rstrip().split("-")
				if len(cols) < 3:
					continue
				fsname = cols[0]
				re_result = re.search(".*(\d)", cols[1], re.IGNORECASE)
				target = None
				if re_result:
					target = int(re_result.group(1)[0])
				status = True if "active" in line else False
				if fsname in self.layout:
					if "mdt" in cols[1].lower():
						self.layout[fsname]["mdts_health"][target] = status
					elif "ost" in cols[1].lower():
						self.layout[fsname]["osts_health"][target] = status
		
	
	def initialize(self):	
		for fsname in self.layout:
			host_dir = self.layout[fsname]['wdir'] + os.sep + self.hostname 
			if not os.path.isdir(host_dir):
				os.makedirs(host_dir)

			for ost_id in self.layout[fsname]['osts']:
				# create ost file for wrex
				ost_dir = host_dir + os.sep + str(ost_id)
				if not os.path.isdir(ost_dir):
					os.makedirs(ost_dir)
				ost_file = ost_dir + os.sep + str(ost_id) + ".wrex"
				if os.path.isfile(ost_file):
					if __checkstripe__([ost_file, ost_id]) == False:
						os.remove(ost_file)
						__setstripe__([ost_file, ost_id])
				else:
					__setstripe__([ost_file, ost_id])
				# create crwr dirs
				dirname = ost_dir + os.sep + "crwr"
				if os.path.isdir(dirname):
					continue
				else:
					os.makedirs(dirname)

	def clean(self):
		for fsname in self.layout:
			dirname = self.layout[fsname]['wdir']
			print(dirname)
			shutil.rmtree(dirname)
       # todo : such an arrangement does not allow for each probe to have its own timeout	
	def get_ost_tasks(self):
		self.ost_tasks = []
		for fsname in self.layout:
			for ost_id in self.layout[fsname]['osts']:
				per_ost_task = []
				pb_id = 1 # wrex
				ost_file = self.layout[fsname]['wdir'] + os.sep + self.hostname + os.sep +  str(ost_id) + os.sep + str(ost_id) + ".wrex"
				per_ost_task.append([fsname, ost_id, pb_id, ost_file])
				pb_id = 2 # crwr
				ost_file = self.layout[fsname]['wdir'] + os.sep + self.hostname + os.sep  + str(ost_id) + os.sep + "crwr" + os.sep + "test.tmp"
				per_ost_task.append([fsname, ost_id, pb_id, ost_file])
				pb_id = 3 # rmex
				per_ost_task.append([fsname, ost_id, pb_id, ost_file])
				self.ost_tasks.append(per_ost_task)
				
	def get_mdt_tasks(self):
		ost_id = -1
		self.mdt_tasks = []
		for fsname in self.layout:
			pb_id = 4 # lsex
			self.mdt_tasks.append([fsname, ost_id, pb_id, self.layout[fsname]['wdir']])

	def get_tasks(self):
		self.get_ost_tasks()
		self.get_mdt_tasks()

	def write(self, odir):
		with open(odir + os.sep + "qos_" + self.hostname + ".log", 'w') as ofh:
			for row in self.db:
				try:
					ofh.write(",".join(map(str, row)) + "," + str(self.hostname) + "\n")
				except Exception as e:
					print("row:", row)
					print("error", e)
					continue
			ofh.close()
				
	def run(self):
		self.get_tasks()
		p = multiprocessing.Pool(self.threads)
		abortable_func_ost = partial(abortable_worker, __k_ost__, timeout=self.timeout)
		abortable_func_mdt = partial(abortable_worker, __k_mdt__, timeout=self.timeout)
		for task in  self.ost_tasks:
			p.apply_async(abortable_func_ost, args=[task],callback=self.db.extend)	
		for task in  self.mdt_tasks:
			p.apply_async(abortable_func_mdt, args=[task],callback=self.db.extend)
		p.close()
		p.join()


def main(args):
	ksp = KSProbes(args.threads, args.timeout, args.config)
	#pprint(ksp.layout)
	if args.init == True:
		ksp.initialize()
		pprint(ksp.layout)
	elif args.clean == True:
		ksp.clean()
	if True:
	# get probe tasks
		lt = time.time()
		epoch_time = int(args.epoch_time)
		num_runs = 0
		while True:
			curr_time = time.time()
			if curr_time - lt >= epoch_time:
				lt = curr_time 
				ksp.run()
				num_runs += 1
			if num_runs >= int(args.total_runs):
				break
		ksp.write(args.odir)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--init", help="create directory structure", required = False, action="store_true")
	parser.add_argument("--threads", help="#threads", required = False, default = 64)
	parser.add_argument("--epoch_time", help="collection every epoch_time seconds", required = False, default = 30)
	parser.add_argument("--total_runs", help="quit application after collecting total_runs epochs", required = False, default = 2)
	parser.add_argument("--timeout", help="timeout for probes", required = False, default = 30)
	parser.add_argument("--config", help="config file", required = False, default="config")
	parser.add_argument("--clean", help = "delete directory structure", required = False, action = "store_true")
	parser.add_argument("--odir", help = "output dir", required = False, default="./")
	args = parser.parse_args()
	main(args)
