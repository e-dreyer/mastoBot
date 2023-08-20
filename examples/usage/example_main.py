from typing import List, Dict
from jinja2 import Environment, FileSystemLoader
import logging
import re

from mastoBot.configManager import ConfigAccessor
from mastoBot.mastoBot import MastoBot, handleMastodonExceptions

class MyBot(MastoBot):
    @handleMastodonExceptions
    def processUpdate(self, notification: Dict):
        pass
    
    @handleMastodonExceptions
    def processMention(self, mention: Dict):
        # Get the content from the mention
        content = self.getStatus(mention.get("status")).get("content")

        # Check for report tag
        report_pattern = r"(.*?)(?<!\S)\$report\b\s*(.*)</p>"
        report_match = re.search(report_pattern, content)
        if report_match:
            before_report = report_match.group(1).strip()
            report_message = report_match.group(2).strip()
            logging.info(f"Report message received: {report_message}")

            # Get account
            api_account = self.getAccount(mention.get("account"))
            api_status = self.getStatus(mention.get("status"))

            try:
                file_loader = FileSystemLoader("templates")
                env = Environment(loader=file_loader)
                template = env.get_template("report.txt")

                output = template.render(
                    creator=api_account.get("acct"),
                    reported_post_id=mention.get("status"),
                    reported_post_url=api_status.get("url"),
                    report_message=report_message,
                )
            except Exception as e:
                logging.critical("Error initializing template")
                raise e

            try:
                self._api.status_post(status=output, visibility="direct")
            except Exception as e:
                logging.critical("Error posting status message")
                raise e
        else:
            # Perform actions after calling the original function
            if self.shouldReblog(mention.get("status")):
                try:
                    self.reblogStatus(mention.get("status"))
                except Exception as e:
                    logging.warning(
                        f"Status could not be boosted: {mention.get('status')}"
                    )
                    logging.error(e)

            if self.shouldFavorite(mention.get("status")):
                try:
                    self.favoriteStatus(mention.get("status"))
                except Exception as e:
                    logging.warning(
                        f"Status could not be favourited: {mention.get('status')}"
                    )
                    logging.error(e)

        logging.info(f"Mention processed: {mention.get('id')}")
        self.dismissNotification(mention.get("id"))

    @handleMastodonExceptions
    def processReblog(self, reblog: Dict):
        self.dismissNotification(reblog.get("id"))

    @handleMastodonExceptions
    def processFavourite(self, favourite: Dict):
        self.dismissNotification(favourite.get("id"))

    @handleMastodonExceptions
    def processFollow(self, follow: Dict):
        # Get latest account from the Mastodon API
        api_account = self.getAccount(follow.get("account"))
        account = api_account.get("acct")

        try:
            file_loader = FileSystemLoader("templates")
            env = Environment(loader=file_loader)
            template = env.get_template("new_follow.txt")
            output = template.render(account=account)
        except Exception as e:
            logging.critical("Error initializing template")
            raise e

        # Generate the welcoming message from the template
        try:
            self._api.status_post(status=output, visibility="direct")
        except Exception as e:
            logging.critical("Error posting Status")
            raise e

        logging.info(f"Follow processed: {follow.get('id')}")
        self.dismissNotification(follow.get("id"))

    @handleMastodonExceptions
    def processPoll(self, poll: Dict):
        self.dismissNotification(poll.get("id"))

    @handleMastodonExceptions
    def processFollowRequest(self, follow_request: Dict):
        self.dismissNotification(follow_request.get("id"))

    @handleMastodonExceptions
    def isParentStatus(self, status_id: int) -> bool:
        api_status = self.getStatus(status_id)
        if api_status.get("in_reply_to_id"):
            return False
        else:
            return True

    @handleMastodonExceptions
    def isByFollower(self, status_id: int) -> bool:
        api_mention = self.getStatus(status_id)
        relationships = self._api.account_relationships(api_mention.get("account"))
        return relationships[0].get("followed_by", False)

    @handleMastodonExceptions
    def shouldReblog(self, status_id: int) -> bool:
        isParentStatus = self.isParentStatus(status_id)
        isByFollower = self.isByFollower(status_id)
        boostConfig = self.config["boosts"]

        if isParentStatus and boostConfig["parents"]:
            if boostConfig["followers_only"]:
                return isByFollower
            else:
                return True
        elif not isParentStatus and boostConfig["children"]:
            if boostConfig["followers_only"]:
                return isByFollower
            else:
                return True
        else:
            return False

    @handleMastodonExceptions
    def shouldFavorite(self, status_id: int) -> bool:
        isParentStatus = self.isParentStatus(status_id)
        isByFollower = self.isByFollower(status_id)
        favoriteConfig = self.config["favorites"]

        if isParentStatus and favoriteConfig["parents"]:
            if favoriteConfig["followers_only"]:
                return isByFollower
            else:
                return True
        elif not isParentStatus and favoriteConfig["children"]:
            if favoriteConfig["followers_only"]:
                return isByFollower
            else:
                return True
        else:
            return False

if __name__ == "__main__":
    config = ConfigAccessor("config.yml")
    credentials = ConfigAccessor("credentials.yml")

    bot = MyBot(credentials=credentials, config=config)

    bot.run()
