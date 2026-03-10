from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy
from app.config import settings
import logging

logger = logging.getLogger(__name__)
_session = None

def get_session():
    global _session
    if _session is None:
        cluster = Cluster(
            contact_points=[settings.CASSANDRA_HOST],
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
        )
        _session = cluster.connect()
    return _session

def init_cassandra():
    session = get_session()
    session.set_keyspace(settings.CASSANDRA_KEYSPACE)
    logger.info("Cassandra connecté (lecture seule).")
