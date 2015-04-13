#!/usr/bin/env python
"""Collect the latest social stats for Gluster projects

Grabs watchers, stars, forks, and # of commits per day.
Needs code added to grab total # of downloads per day (when available).

Requires the SQLite3 Python module
"""

import os, os.path, sys, ConfigParser
import sqlite3
import requests
import json
from datetime import datetime

# Enable this to have the results printed to stdout
debug = True

# Read the GitHub projects from the ./config file
config_file_path = 'config'
config = ConfigParser.SafeConfigParser()
config.read(config_file_path)

# Open the ./stats.db SQLite3 database
db_path = 'db/project_stats.db'
conn = sqlite3.connect(db_path)

# Connect to the database
c = conn.cursor()

# Create the SQLite3 table to store the info, if it's not already present
sql = ('CREATE TABLE IF NOT EXISTS social_stats (project TEXT, time_stamp TEXT, '
       'watchers INTEGER, stars INTEGER, forks INTEGER, commits INTEGER, downloads INTEGER)')
c.execute(sql)
conn.commit()

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
    watchers = api_data['watchers']
    stars = api_data['stargazers_count']
    forks = api_data['forks_count']

    # Count the # of commits since midnight
    commits_url = '{0}/commits?since={1}T00:00:00Z'.format(api_url, datetime.now().date().isoformat())
    commits_page = requests.get(commits_url, verify=True)
    if commits_page.status_code != 200:
        print 'Error retrieving Commit count page {0}'.format(commits_url)
        print '  Status code {0}'.format(commits_page.status_code)
        sys.exit(2)
    commits_data = json.loads(commits_page.text)
    commits_count = len(commits_data)

    # Print the results to stdout
    if debug:
        print '{0} - commits: {1}\twatchers: {2}\tstars: {3}\tforks: {4}\n'.format(project, commits_count,
                                                                                   watchers, stars, forks)

    # Add the results to the database
    sql = ('INSERT INTO social_stats (project, time_stamp, watchers, stars, forks, commits) VALUES '
           "('{0}', date('now'), '{1}', '{2}', '{3}', '{4}')").format(project, watchers, stars, forks, commits_count)
    c.execute(sql)
    conn.commit()

# Close the database connection
c.close()
