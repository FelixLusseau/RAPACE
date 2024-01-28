# RAPACE

[![Author](https://img.shields.io/badge/author-@FelixLusseau-blue)](https://github.com/FelixLusseau)
[![Author](https://img.shields.io/badge/author-@Alia77-blue)](https://github.com/Alia77)
[![Author](https://img.shields.io/badge/author-@Louciaul-blue)](https://github.com/Louciaul)

<a href="https://p4.org/" target="_blank" rel="noreferrer"> <img src="https://upload.wikimedia.org/wikipedia/commons/1/12/P4-programming-language-logo.png" alt="p4" width="40" height="40"/> </a> 
<a href="https://www.python.org" target="_blank" rel="noreferrer"> <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="40" height="40"/> </a>

## Description

RAPACE is a Programmable Network composed of 4 programmables P4 Switches types (router, router_lw, firewall and load_balancer) and hosts.

## Installation

Clone the repository and run the following command to install the required dependencies:

```bash
git clone git@github.com:FelixLusseau/RAPACE.git
cd RAPACE
sudo pip3 install -r requirements.txt
```

## Usage

To run the network, write your wanted topology in the `network.yaml` file and run the network with the following command:

```bash
sudo python3 meta_controller.py
```

The network is launched !

You can interact with it through the `RAPACE_CLI>` or via the hosts shell with :

```bash
mx h1
```
