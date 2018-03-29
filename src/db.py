import sqlalchemy
import pandas as pd


class Database:

    def __init__(self, user, password, db, host, port):
        self.user = user
        self.password = password
        self.db = db
        self.host = host
        self.port = port
        self.con, self.meta = self._connect()

    def _connect(self):
        '''Returns a connection and a metadata object'''
        # connect with the help of the PostgreSQL URL
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(self.user, self.password, self.host, self.port, self.db)

        # connection object
        con = sqlalchemy.create_engine(url, client_encoding='utf8')

        # bind the connection to MetaData()
        meta = sqlalchemy.MetaData(bind=con, reflect=True)

        return con, meta

    def get_filters(self, job_id):
        '''
        :param job_id:
        :return: list of filter id
        '''

        sql_filter_list = '''
                                select c.* from job j 
                                join project p on j.project_id = p.id
                                join criterion c on c.project_id = p.id where j.id = {job_id};
                            '''.format(job_id=job_id)
        filter_array = pd.read_sql(sql_filter_list, self.con)['id'].values
        filter_list = [int(i) for i in filter_array]

        return filter_list

    def get_items_tolabel(self, filter_id, worker_id, job_id):
        '''
        :param filter_id:
        :param worker_id:
        :param job_id:
        :param max_votes:
        :return: list of ids of items to be labeled
        '''
        sql_max_votes = '''
          select data ->> 'votesPerTaskRule' as max_votes from job where id = {job_id}
        '''.format(job_id=job_id)
        max_votes = pd.read_sql(sql_max_votes, self.con)['max_votes'].values[0]

        sql_items_tolabel = '''
                                select i.id, coalesce(item_votes.votes, 0) as votes 
                                from (select item_id, votes from 
                                  (select t.item_id, count(t.*) as votes from task t
                                    where t.job_id = {job_id}
                                      and t.data @> '{{"criteria" : [{{"id": "{filter_id}"}}]}}'
                                      and t.data ->> 'answered' = 'true'
                                    group by t.item_id
                                  ) v 
                                  where votes < {max_votes}
                                        and item_id not in (
                                          select t.item_id from task t
                                          where t.job_id = {job_id}
                                                and t.worker_id = {worker_id}
                                                and t.data @> '{{"criteria" : [{{"id": "{filter_id}"}}]}}'
                                                and t.data ->> 'answered' = 'true'
                                        )
                                ) item_votes right join item i on i.id = item_votes.item_id
                                where i.id not in (
                                  select t.item_id from task t
                                    where t.job_id = {job_id}
                                      and t.worker_id = {worker_id}
                                      and t.data @> '{{"criteria" : [{{"id": "{filter_id}"}}]}}'
                                      and t.data ->> 'answered' = 'true'
                                );
                            '''.format(filter_id=filter_id, worker_id=worker_id, job_id=job_id, max_votes=max_votes)

        items_tolabel = pd.read_sql(sql_items_tolabel, self.con)['id'].values
        items_tolabel = [int(i) for i in items_tolabel]

        return items_tolabel
