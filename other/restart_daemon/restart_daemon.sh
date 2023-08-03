#!/bin/bash

sudo systemctl stop lockauth.service

sleep 5

sudo systemctl disable lockauth.service

sudo systemctl daemon-reload

sudo systemctl enable lockauth.service

sudo systemctl start lockauth.service