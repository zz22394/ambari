#!/usr/bin/env python

'''
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import os
import sys
import logging
import json
from coilmq.util import frames
from coilmq.util.frames import Frame

from BaseStompServerTestCase import BaseStompServerTestCase

from ambari_agent import HeartbeatThread
from ambari_agent.InitializerModule import initializer_module

from mock.mock import MagicMock, patch

class TestAgentStompResponses(BaseStompServerTestCase):
  def test_mock_server_can_start(self):
    self.init_stdout_logger()

    #initializer_module.server_hostname = 'gc6401'
    #initializer_module.init()

    self.remove(['/tmp/configurations.json', '/tmp/metadata.json', '/tmp/topology.json'])

    heartbeat_thread = HeartbeatThread.HeartbeatThread()
    heartbeat_thread.heartbeat_interval = 0
    heartbeat_thread.start()

    connect_frame = self.server.frames_queue.get()
    users_subscribe_frame = self.server.frames_queue.get()
    commands_subscribe_frame = self.server.frames_queue.get()
    configurations_subscribe_frame = self.server.frames_queue.get()
    metadata_subscribe_frame = self.server.frames_queue.get()
    topologies_subscribe_frame = self.server.frames_queue.get()
    registration_frame = self.server.frames_queue.get()

    # server sends registration response
    f = Frame(frames.MESSAGE, headers={'destination': '/user/', 'correlationId': '0'}, body=self.get_json("registration_response.json"))
    self.server.topic_manager.send(f)

    f = Frame(frames.MESSAGE, headers={'destination': '/events/configurations'}, body=self.get_json("configurations_update.json"))
    self.server.topic_manager.send(f)

    f = Frame(frames.MESSAGE, headers={'destination': '/events/commands'}, body=self.get_json("execution_commands.json"))
    self.server.topic_manager.send(f)

    f = Frame(frames.MESSAGE, headers={'destination': '/events/metadata'}, body=self.get_json("metadata_after_registration.json"))
    self.server.topic_manager.send(f)

    f = Frame(frames.MESSAGE, headers={'destination': '/events/topologies'}, body=self.get_json("topology_update.json"))
    self.server.topic_manager.send(f)

    heartbeat_frame = self.server.frames_queue.get()
    heartbeat_thread._stop.set()

    f = Frame(frames.MESSAGE, headers={'destination': '/user/', 'correlationId': '1'}, body=json.dumps({'heartbeat-response':'true'}))
    self.server.topic_manager.send(f)

    heartbeat_thread.join()

    self.assertEquals(initializer_module.topology_cache['cl1']['topology']['hosts'][0]['hostname'], 'c6401.ambari.apache.org')
    self.assertEquals(initializer_module.metadata_cache['cl1']['metadata']['status_commands_to_run'], ('STATUS',))
    self.assertEquals(initializer_module.configurations_cache['cl1']['configurations']['zoo.cfg']['clientPort'], '2181')

    """
    ============================================================================================
    ============================================================================================
    """

    delattr(initializer_module,'_connection')
    self.server.frames_queue.queue.clear()

    heartbeat_thread = HeartbeatThread.HeartbeatThread()
    heartbeat_thread.heartbeat_interval = 0
    heartbeat_thread.start()

    connect_frame = self.server.frames_queue.get()
    users_subscribe_frame = self.server.frames_queue.get()
    commands_subscribe_frame = self.server.frames_queue.get()
    configurations_subscribe_frame = self.server.frames_queue.get()
    metadata_subscribe_frame = self.server.frames_queue.get()
    topologies_subscribe_frame = self.server.frames_queue.get()
    registration_frame_json = json.loads(self.server.frames_queue.get().body)
    clusters_hashes = registration_frame_json['clusters']['cl1']

    self.assertEquals(clusters_hashes['metadata_hash'], '20089c8c8682cf03e361cdab3e668ed1')
    self.assertEquals(clusters_hashes['configurations_hash'], 'bc54fe976cade95c48eafbfdff188661')
    self.assertEquals(clusters_hashes['topology_hash'], 'd14ca943e4a69ad0dd640f32d713d2b9')

    # server sends registration response
    f = Frame(frames.MESSAGE, headers={'destination': '/user/', 'correlationId': '0'}, body=self.get_json("registration_response.json"))
    self.server.topic_manager.send(f)

    heartbeat_frame = self.server.frames_queue.get()
    heartbeat_thread._stop.set()

    f = Frame(frames.MESSAGE, headers={'destination': '/user/', 'correlationId': '1'}, body=json.dumps({'heartbeat-response':'true'}))
    self.server.topic_manager.send(f)

    heartbeat_thread.join()

  def remove(self, filepathes):
    for filepath in filepathes:
      if os.path.isfile(filepath):
        os.remove(filepath)

  def init_stdout_logger(self):
    format='%(levelname)s %(asctime)s - %(message)s'

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(format)
    chout = logging.StreamHandler(sys.stdout)
    chout.setLevel(logging.INFO)
    chout.setFormatter(formatter)
    cherr = logging.StreamHandler(sys.stderr)
    cherr.setLevel(logging.ERROR)
    cherr.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(cherr)
    logger.addHandler(chout)

    logging.getLogger('stomp.py').setLevel(logging.WARN)
    logging.getLogger('coilmq').setLevel(logging.INFO)