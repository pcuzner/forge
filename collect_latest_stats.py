#!/usr/bin/env python
"""Collect the latest social stats for Gluster projects

Grabs watchers, stars, forks, # of commits per day, and total number of downloads (ever).

Requires the SQLite3 Python module
"""

import os, os.path, sys, ConfigParser
import sqlite3
import requests
import json

# Enable this to have the results printed to stdout
debug = True

# Read the GitHub projects from the ./config file
base_path = os.path.dirname(os.path.realpath(__file__))
config_file_path = os.path.join(base_path, 'config')
config = ConfigParser.SafeConfigParser()
config.read(config_file_path)

# Open the ./db/project_stats.db SQLite3 database
db_path = os.path.join(base_path, 'db/project_stats.db')
conn = sqlite3.connect(db_path)

# Connect to the database
c = conn.cursor()

# Create the SQLite3 table to store the info, if it's not already present
sql = ('CREATE TABLE IF NOT EXISTS social_stats (project TEXT, time_stamp TEXT, '
       'watchers INTEGER, stars INTEGER, forks INTEGER, commits INTEGER, downloads INTEGER)')
c.execute(sql)
conn.commit()

# Retrieve today and yesterday (as formatted strings) from the database
sql = "SELECT strftime('%Y-%m-%dT%H:%M:%S', 'now'), strftime('%Y-%m-%dT%H:%M:%S', 'now', '-1 day')"
c.execute(sql)
sql_results = c.fetchall()
today = sql_results[0][0]
yesterday = sql_results[0][1]

# Loop through the projects in the config file
for project in config.sections():

    # Construct the GitHub API URL for the project
    api_url = 'https://api.github.com/repos/' + project

    # Retrieve the (json) API page
    api_page = requests.get(api_url, verify=True)
    if api_page.status_code != 200:
        print 'Error retrieving API page {0}'.format(api_url)
        print '  Status code {0}'.format(api_page.status_code)
        sys.exit(1)
    api_data = json.loads(api_page.text)

    # Extract the number of watchers, stars, and forks
    watchers = api_data['subscribers_count']
    stars = api_data['stargazers_count']
    forks = api_data['forks_count']

    # Count the # of commits in the last 24 hours
    commits_url = '{0}/commits?since={1}Z'.format(api_url, yesterday)
    commits_page = requests.get(commits_url, verify=True)
    if commits_page.status_code != 200:
        print 'Error retrieving Commit count page {0}'.format(commits_url)
        print '  Status code {0}'.format(commits_page.status_code)
        sys.exit(2)
    commits_data = json.loads(commits_page.text)
    commits_count = len(commits_data)

    # Retrieve the downloads page for this project
    download_counter = 0
    dl_url = '{0}/releases'.format(api_url)
    dl_page = requests.get(dl_url, verify=True)
    if dl_page.status_code != 200:
        print 'Error retrieving downloads count page {0}'.format(dl_url)
        print '  Status code {0}'.format(dl_page.status_code)
        sys.exit(3)
    dl_data = json.loads(dl_page.text)

    # Note - For each project there is an outer loop of "releases" (eg v3.6.0), with an inner loop of "assets" inside
    # each release (with each asset having it's own download counter). eg: an .exe and a .dmg might be two assets in
    # the same v3.6.0 release.  The .exe might have 10,000 downloads, and the .dmg might have 3,000.

    # Count how many downloads have occurred (ever) for the project
    if len(dl_data) > 0:
        for release in dl_data:
            for asset in release['assets']:
                download_counter += asset['download_count']

    # Print the results to stdout
    if debug:
        print ('{0}\n\tcommits: {1}\twatchers: {2}\tstars: {3}\tforks: {4}\t'
               'downloads: {5}\n'.format(project, commits_count, watchers, stars, forks, download_counter))

    # Add the results to the database
    sql = ('INSERT INTO social_stats (project, time_stamp, watchers, stars, forks, commits, downloads) VALUES '
           "('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')").format(project, today, watchers, stars, forks,
                                                                       commits_count, download_counter)
    c.execute(sql)
    conn.commit()

# Close the database connection
c.close()