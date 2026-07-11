Discord bot named "Picklebot"

has the following features:
- send daily news articles to 'pickle news' category channels via NewsAPI
  - respective channels include: pickleball competition, pickleball consumer, pickleball tech
- sends weekly meet-up reminders via reminder channel-webhook (could also just use channel ID, but for sake of experimentation)
- creates weekly scheduled events in server for meet-up w/ editable titles and descriptions enabled by admins/owners  @9:00 PM EST
  - datetime.today().weekday() == 5 -> 5 is Saturday
- sends a survery (poll) private DM to remind members to attend meeting  @8:30 PM EST day prior to meeting
  - datetime.today().weekday() == 4 -> 4 is Friday

runs asynchronously (should be w/ out issues, else try/except clauses are abundant and will aid w/ debugging)
uses sqlmodel ORM & automatic validation to manage the db file 'picklebot_news_state.db'
