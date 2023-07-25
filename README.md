# MastoBot

A generic bot that allows anyone to create group bots on Mastodon.

## Motivation

Mastodon allows for the use of hashtags on the platform. Users can use these hashtags to allow others to subscribe to topics and search for trends. These hashtags however suffer from the lack of moderation. Malicious users are able to hijack trends and topics by simply using the tags in their posts. Users are unable to avoid such post except for muting or blocking such users.

As Mastodon has grown in popularity the need for larger communities and discussions has grown. This bot allows users to mention the username of the bot, no different from mentioning any other user. The bot can then perform certain actions on this post. This most common reaction is to boost the post for other users following the bot to see. Moderators can then remove rule-breaking posts, block user on their current account and new accounts they move to and run various other automation. Such groups can also be made open-source to allow the community to contribute to the development of the bot. Such groups grant moderators more granular control and allows for an improved experience for communities.

## Implementation

## Features

### Templates

In order to allow for a generic implementation and usage of this implementation `Jinja2` templates have been used for all personalized messages sent to users. This allows a group to customize the message to their like which is sent to new followers as an example.

## Configuration

### Config.py

`config.py` is used to load custom configs and modified implementations. It allows for the specification of parameters that change the behavior of the bot.

### Credentials.py

`credentials.py` is used to load custom credentials and is kept separate to allow for the sharing of configs and implementations, but keeping credentials secret.

Currently the following credentials are implemented and should be provided in `credentials.yml`:

- mastodon:
    secret: Your Mastodon `secret` key, found under `development` in your settings
    base_url: Your base `url` for my instance it would be `"https://techhub.social/"`

### Docker

For simplicity the main focus of this bot has been to develop it to run in `Docker`. This allows for a simpler deployment of the bot and binds all of its components together. It also allows less technical users to easily host multiple bots and track their performance.