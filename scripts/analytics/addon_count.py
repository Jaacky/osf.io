import sys
import logging
from datetime import datetime
from dateutil.parser import parse

from website.settings import ADDONS_AVAILABLE
from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def count():
    counts = []
    for addon in ADDONS_AVAILABLE:
        user_count = addon.settings_models['user'].find().count() if addon.settings_models.get('user') else 0
        node_count = addon.settings_models['node'].find().count() if addon.settings_models.get('node') else 0
        counts.append({
            'provider': addon.short_name,
            'user_count': user_count,
            'node_count': node_count
        })

        logger.info('{} counted. Users: {}, Nodes: {}'.format(addon.short_name, user_count, node_count))
    return counts

def main():
    addon_count = count()
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_event('addon_count_analytics', addon_count)
    else:
        print(addon_count)


if __name__ == '__main__':
    init_app()
    try:
        date = parse(sys.argv[1])
    except IndexError:
        date = datetime.now()
    main(date)
