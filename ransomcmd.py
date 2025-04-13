#!/usr/bin/env python3
"""
Ransomware.live 

Description:
    Ransomware.live is a comprehensive command-line tool designed to manage and monitor ransomware activities.
    It supports various functionalities including scraping ransomware DLS (Dark Leak Sites), parsing the collected data,
    generating reports and graphs, taking screenshots of ransomware sites, and more.

    The program is built with extensibility in mind, allowing for easy addition of new features and integration with
    existing tools and libraries.

Usage:
    python3 ransomcmd.py <command> [options]

Dependencies:
    - Python 3.x
    - Python packages: sys, os, asyncio, argparse, dotenv, hashlib, time, importlib, glob, datetime, atexit, tempfile

Environment Variables:
    - Managed via a `.env` file, which includes configurations for directories, data files, etc.

Author:
    Julien Mousqueton

Version:
    2.0.0
"""

import sys
import os
import json
import asyncio
import argparse
from dotenv import load_dotenv 
import hashlib
import time
from os.path import join, dirname, isfile, basename
from datetime import datetime 
## For lockfile
import tempfile
import subprocess
import re

import uvicorn

## Import Ransomware.live libs 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'libs')))
import ransomwarelive 
from generatesite import writeline, month_name,month_digit
import generatesite 
import graph
import rss
import ransomnotes 
import hudsonrock
import negotiations
import mystripe

SOURCE='./source'

## Functions

def get_process_info():
    processes = []
    try:
        ps_output = subprocess.check_output(['ps', '-ef']).decode('utf-8')
        for line in ps_output.split('\n'):
            if 'python3 ransomcmd.py' in line and any(proc in line for proc in ['scrape', 'parse', 'generate']):
                parts = line.split()
                process_name = parts[-1]
                process_id = parts[1]
                elapsed_seconds = int(subprocess.check_output(['ps', '-p', process_id, '-o', 'etimes=']).decode('utf-8').strip())
                elapsed_minutes = elapsed_seconds // 60
                processes.append((process_name, process_id, elapsed_minutes))
    except Exception as e:
        print(f"Error occurred: {e}")
    return processes

def process_parse_info(process_id, elapsed_minutes):
    try:
        lsof_output = subprocess.check_output(['lsof', '-p', process_id]).decode('utf-8')
        html_files = [line for line in lsof_output.split('\n') if '.html' in line]
        if html_files:
            for file in html_files:
                match = re.search(r'source/(.+?)-', file)
                if match:
                    group_name = match.group(1)
                    print(f"The \033[1mparse\033[0m process (PID: {process_id}) is running since {elapsed_minutes} minutes with group: \033[1m{group_name}\033[0m")
        else:
            print(f"The \033[1mparse\033[0m process (PID: {process_id}) is running since {elapsed_minutes} minutes, but no HTML files are currently open.")
    except Exception as e:
        print(f"Error occurred while processing 'parse': {e}")

def main():
    print(
    '''
       _______________                        |*\\_/*|________
      |  ___________  |                      ||_/-\\_|______  |
      | |           | |                      | |           | |
      | |   0   0   | |                      | |   0   0   | |
      | |     -     | |                      | |     -     | |
      | |   \\___/   | |                      | |   \\___/   | |
      | |___     ___| |                      | |___________| |
      |_____|\\_/|_____|                      |_______________|
        _|__|/ \\|_|_.............💔.............._|________|_
       / ********** \\                          / ********** \\ 
     /  ************  \\  Ransomware.live NG  /  ************  \\ 
    --------------------                    --------------------
    '''
    )
    
    VICTIMS_FILE = os.getenv('DATA_DIR') + os.getenv('VICTIMS_FILE')
    
    if not os.path.isfile(VICTIMS_FILE):
        # this is required to prevent things from breaking if the correct JSON structure is not yet present
        ransomwarelive.errlog(f'Victims file is empty - creating a new one: {VICTIMS_FILE}')
        newpost = []
        newpost.append(ransomwarelive.posttemplate("", "", str(datetime.today()),"","",str(datetime.today()),"","",""))
        with open(VICTIMS_FILE, 'w', encoding='utf-8') as jsonfile:
            json.dump(newpost,jsonfile)
    
    # Create the top-level parser
    parser = argparse.ArgumentParser()

    parser.add_argument('--api', nargs='?', const=8080, type=int, help='Run as HTTP API instead of CLI, optional port (default: 8080)')

    subparsers = parser.add_subparsers(dest='command')

    # Create sub-parser for 'scrape'
    parser_scrape = subparsers.add_parser('scrape', help='Scrape ransomware DLS sites (use -h/--help for available options)')
    parser_scrape.add_argument('-F', '--force', action='store_true', help='Force scraping')
    parser_scrape.add_argument('-g', '--group', type=str, help='Specify a specific group to scrape')

    # Create sub-parser for 'parse'
    parser_parse = subparsers.add_parser('parse', help='Parse ransomware DLS sites (use -h/--help for available options)')
    parser_parse.add_argument('-g', '--group', type=str, help='Specify a specific group to parse')

    # Create sub-parser for 'generate'
    parser_generate = subparsers.add_parser('generate', help='Generate Ransomware.live site')

    parser_screenshot = subparsers.add_parser('screenshot', help='Generate screenshot for ransomware sites (use -h/--help for available options)')
    parser_screenshot.add_argument('-g', '--group', type=str, help='Specify a specific group to screenshot')
    parser_screenshot.add_argument('-u', '--url', type=str, help='Specify a specific url to screenshot')

    parser_status = subparsers.add_parser('status', help='Show the status of ransomware.live')

    parser_search = subparsers.add_parser('search', help='Search victim in database (use -h/--help for available options)')
    parser_search.add_argument('-v', '--victim', type=str, help='Specify a victim name or domain')

    parser_recentvictims = subparsers.add_parser('recentvictims', help='Search most recent victims in database (use -h/--help for available options)')
    parser_recentvictims.add_argument('-g', '--group', type=str, default="all", help='Specify a group name')
    parser_recentvictims.add_argument('-c', '--count', type=int, default=10, help='Number of victims to return')
    parser_recentvictims.add_argument('-s', '--since', type=str, default="1970-01-01 00:00:00", help="Only include entries discovered after this timestamp (format: YYYY-MM-DD HH:MM:SS)")
    
    parser_rss = subparsers.add_parser('rss', help='Generate RSS feeds')

    parser_infostealer = subparsers.add_parser('infostealer', help='Add infostealer information from  Hudsonrock database (need -d/--domain <domain>)')
    parser_infostealer.add_argument('-d', '--domain', type=str, help='Specify a victim domain')

    # Create sub-parser for 'tools'
    parser_tools = subparsers.add_parser('tools', help='Tools for Ransomware.live (use -h/--help for available options)')
    tools_subparsers = parser_tools.add_subparsers(dest='tool_command')
    # Create sub-parser for 'tools duplicate'
    parser_tools_duplicate = tools_subparsers.add_parser('duplicate', help='Remove duplicate source files')
    parser_tools_order = tools_subparsers.add_parser('order', help='Order groups by alphabetic order')
    parser_tools_blur = tools_subparsers.add_parser('blur', help='Blur a picture (need -f/--file option)')
    parser_tools_blur.add_argument('-f', '--file', type=str, help='full path of the image to blur')


    parser_add = subparsers.add_parser('add', help='Add a new ransomware group (need -n/--name and -l/--location options)')
    parser_add.add_argument('-n', '--name', type=str, help='specify the ransomware group name')
    parser_add.add_argument('-l', '--location', type=str, help='specify the ransomware group site')

    parser_append = subparsers.add_parser('append', help='Add a new ransomware site to an existing group (need -n/--name and -l/--location options)')
    parser_append.add_argument('-n', '--name', type=str, help='specify the ransomware group name')
    parser_append.add_argument('-l', '--location', type=str, help='specify the ransomware group site')

    # Parse the arguments
    args = parser.parse_args()

    if args.api is not None:
        uvicorn.run("ransomwarelive:app", host="0.0.0.0", port=args.api, reload=True)
    else:
        # Execute the appropriate function based on the provided subcommand
        if args.command == ('add' or 'append') and (args.name is None or args.location is None):
            parser.error("operation requires -n/--name and -l/--location")
        
        if args.command == 'add':
            ransomwarelive.siteadder(args.name, args.location)

        elif args.command == 'append':
            ransomwarelive.siteappender(args.name, args.location)

        elif args.command == 'status':
            ransomwarelive.check_lock_file()
            processes = get_process_info()
            if processes:
                for process_name, process_id, elapsed_minutes in processes:
                    bold_process_name = f"\033[1m{process_name}\033[0m"
                    if process_name == 'parse':
                        process_parse_info(process_id, elapsed_minutes)
                    else:
                        print(f"The {bold_process_name} process (PID: {process_id}) is running since {elapsed_minutes} minutes")
            else:
                print(" (!) None of the Ransomware.live processes are running")
        
        elif args.command == 'scrape':
            if args.group:
                asyncio.run(ransomwarelive.scrapegang(args.group,force=args.force))
            else: 
                LOCK_FILE_NAME = "scrape.lock"
                LOCK_FILE_PATH = os.path.join(tempfile.gettempdir(), LOCK_FILE_NAME)
                ransomwarelive.create_lock_file(LOCK_FILE_PATH)  
                start_time = time.time()
                asyncio.run(ransomwarelive.scrape(force=args.force))
                ransomwarelive.remove_duplicate_files(SOURCE)
                end_time = time.time()
                execution_time = end_time - start_time
                ransomwarelive.stdlog(f'Scraping execution time {execution_time:.2f} secondes')
                ransomwarelive.remove_lock_file(LOCK_FILE_PATH)
        
        elif args.command == 'parse':
            asyncio.run(ransomwarelive.parse(args.group))
        
        elif args.command == 'generate':
            LOCK_FILE_NAME = "generate.lock"
            LOCK_FILE_PATH = os.path.join(tempfile.gettempdir(), LOCK_FILE_NAME)
            ransomwarelive.create_lock_file(LOCK_FILE_PATH)  
            start_time = time.time()
            generatesite.mainpage()
            generatesite.statuspage()
            generatesite.summaryjson()
            load_dotenv()
            DATA_DIR = os.getenv('DATA_DIR')
            VICTIMS_FILE = os.getenv('VICTIMS_FILE')
            VICTIMS_FILE = DATA_DIR + VICTIMS_FILE
            GROUPS_FILE = os.getenv('GROUPS_FILE')
            GROUPS_FILE = DATA_DIR + GROUPS_FILE
            hudsonrockfile = DATA_DIR + 'hudsonrock.json'  
            if os.path.getmtime(VICTIMS_FILE) > (time.time() - 2700):
                ransomwarelive.stdlog('Victims database has been modified within the last 45 mins, assuming new posts discovered and generating full site')
                data = ransomwarelive.openjson(hudsonrockfile)
                # Iterate through the entries and apply the conditions
                for key, value in data.items():
                    if value['employees'] > 0 or value['users'] > 0:
                        generatesite.write_domain_info(key, value['employees'], value['users'], value['thirdparties'], value['employees_url'], value['users_url'], value['update'])
                ransomwarelive.update_groups_intel()
                generatesite.ttps()
                ransomwarelive.ttps2json('./import/Ransomware-Tool-Matrix/Tools', './data/ttps.json')
                generatesite.recentdiscoveredpage()
                generatesite.recentattackedpage()
                generatesite.lastvictimspergroup()
                generatesite.profilepage()
                generatesite.groupprofilepage()
                generatesite.allposts()
                generatesite.yara()
                rss.generate_rss_feed()
                year=datetime.now().year
                month=datetime.now().month
                graph.trend_posts_per_day()
                graph.plot_posts_by_group() 
                graph.pie_posts_by_group()
                ransomwarelive.stdlog('generating stats graph per month')
                graph.plot_victims_by_month()
                graph.plot_victims_by_month_cumulative()
                graph.plot_posts_by_group_past_7_days()
                ransomwarelive.stdlog('Creating graphs for '+ str(year))
                graph.pie_posts_by_group_by_year(2024)
                graph.plot_posts_by_group_by_year(2024)
                graph.trend_posts_per_day_2024()
                ransomwarelive.stdlog('generating stats page for ' +  str(year))
                currentgraph = 'docs/stats'+str(year)+'.md'
                graph.plot_group_activity(year)
                with open(currentgraph, 'w', encoding='utf-8') as f:
                        f.close()
                writeline(currentgraph, '# Year '+ str(year) + ' in detail')
                writeline(currentgraph, '') 
                for month in range(1, month+1):
                        ransomwarelive.stdlog('generating stats section for ' +  month_name(month))
                        writeline(currentgraph, '') 
                        writeline(currentgraph, '## '+  month_name(month))
                        writeline(currentgraph, '') 
                        writeline(currentgraph, '| ![](graphs/victims_per_day_' + str(year) + month_digit(month) + '.png) | ![](graphs/postsbygroup' + str(year) + month_digit(month) + '.png) |')
                        writeline(currentgraph, '|---|---|')
                        writeline(currentgraph, '| ![](graphs/grouppie' + str(year) + month_digit(month) + '.png) |  ![](graphs/postsbydayvictims_per_day_' + str(year) + month_digit(month) + '.png)| ')
                        ransomwarelive.stdlog('generating graphs for ' + str(month) + '/' +  str(year))
                        graph.pie_posts_by_group_by_month(year,month)
                        graph.trend_posts_per_day_month(year,month)
                        graph.plot_posts_by_group_by_month(year,month)
                        graph.create_victims_per_day_graph(year,month)
                writeline(currentgraph, '')
                NowTime=datetime.now()
                writeline(currentgraph, 'Last update : _'+ NowTime.strftime('%A %d/%m/%Y %H.%M') + ' (UTC)_')
                ransomwarelive.stdlog('stats for ' +  str(year) + ' generated')    
                graph.wordcloud()
                groups_data = ransomwarelive.openjson(GROUPS_FILE)
                group_names = [group['name'] for group in groups_data]
                ransomwarelive.stdlog("Generate group's victims graph")
                print('[',end="")
                sys.stdout.flush()
                for group_name in group_names:
                    try:
                        graph.statsgroup(group_name)
                        print('*',end="")
                    except:  
                        print('-',end="")
                    sys.stdout.flush()
                print(']')
                # Run the function
                graph.generate_ransomware_map()
                generatesite.generate_country_reports()
            else:
                ransomwarelive.stdlog('posts.json has not been modified within the last 45 mins, assuming no new posts discovered')   
            base_url = "https://www.ransomware.live"
            pages = ransomwarelive.openjson(GROUPS_FILE)
            note_directories = [directory for directory in os.listdir("./docs/notes/") if directory.lower() != ".git.md"]
            generatesite.generate_sitemapXML(base_url, pages, note_directories, output_file="./docs/sitemap.xml")
            ransomwarelive.stdlog('sitemap.xml generated')
            generatesite.generate_sitemapHTML(base_url, pages, note_directories, output_file="./docs/sitemap.html")
            ransomwarelive.stdlog('sitemap.html generated')
            ransomnotes.generate_ransom_notes()
            ransomwarelive.stdlog('Ransom Notes generated')
            for gang in negotiations.get_gangs('./import/Ransomchats'):
                if gang not in ['./importRansomchats/parsers', './import/Ransomchats/.git']:
                    negotiations.parse_group(gang)
            negotiations.generatenegotiationindex()
            ransomwarelive.stdlog('Ransomware Negotiation generated')
            generatesite.json2cvs()
            ### BEGIN : ADMIN ###
            if os.path.getmtime('./docs/admin/budget_sponsors.png') > (time.time() - 86400):
                mystripe.generatestripe()
            graph.generate_execution_time_graphs()
            directory_path = "./docs/admin"
            markdown_file = os.path.join('./docs', "admin.md")
            generatesite.generate_admin_page(directory_path, markdown_file)
            ### END : ADMIN ###
            end_time = time.time()
            execution_time = end_time - start_time
            ransomwarelive.stdlog(f'Generating execution time {execution_time:.2f} secondes')
            ransomwarelive.remove_lock_file(LOCK_FILE_PATH)

        elif args.command == 'screenshot':
            if args.group:
                load_dotenv()
                SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR')
                DATA_DIR = os.getenv('DATA_DIR')
                GROUPS_FILE = os.getenv('GROUPS_FILE')
                GROUPS_FILE = DATA_DIR + GROUPS_FILE
                groups = ransomwarelive.openjson(GROUPS_FILE)
                for group in groups:
                    if group['name'] == args.group:
                        ransomwarelive.stdlog(f'Screenshotter is working on {group["name"]}')
                        for host in group['locations']:
                            ransomwarelive.stdlog(f'Screenshot {host["slug"]}')
                            if not host['enabled']:
                                ransomwarelive.stdlog('Skipping disabled host')
                                continue
                            filename = ransomwarelive.clean_slug(host["fqdn"]).replace(".", "-")
                            filename = f'{SCREENSHOT_DIR}/{filename}.png'
                            asyncio.run(ransomwarelive.screenshot(host["slug"],filename))
            elif args.url:
                load_dotenv()
                POST_SCREENSHOT_DIR = os.getenv('POST_SCREENSHOT_DIR')
                hash_object = hashlib.md5(args.url.encode('utf-8'))
                hex_digest = hash_object.hexdigest()
                filename = os.path.join(POST_SCREENSHOT_DIR, f'{hex_digest}.png')
                asyncio.run(ransomwarelive.screenshot(args.url,filename))
            else:
                asyncio.run(ransomwarelive.screenshotgangs())
        
        elif args.command =="search":
            if args.victim:
                    ransomwarelive.searchvictim(args.victim)
        
        elif args.command =="recentvictims":
            # defaults are group=all, count=10, since=the epoch as per argparse definition
            try:
                since_dt = datetime.strptime(args.since, "%Y-%m-%d %H:%M:%S")
            except:
                ransomwarelive.errlog("Unable to parse value of --since")

            rv = ransomwarelive.recentvictims(group=args.group, count=args.count, since=since_dt)
            print(json.dumps(rv, indent=2))

        elif args.command == "infostealer":
            if args.domain:
                asyncio.run(hudsonrock.run_query(args.domain))
            else:
                parser.print_help()  
        
        elif args.command =="rss":
            ransomwarelive.stdlog('Generate RSS Feed')
            rss.generate_rss_feed()
        
        elif args.command == 'tools' and args.tool_command == 'duplicate':
            ransomwarelive.remove_duplicate_files(SOURCE)
        elif args.command == 'tools' and args.tool_command == 'order':
            ransomwarelive.order_group()
        elif args.command == 'tools' and args.tool_command == 'blur' and args.file is not None: 
            renamed_input_path = ransomwarelive.rename_original_image(args.file)
            if renamed_input_path:
                ransomwarelive.blur_image(renamed_input_path, args.file)
        else:
            parser.print_help()
    # end non-API block

if __name__ == '__main__':
    main()