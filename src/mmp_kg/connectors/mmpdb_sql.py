# -*- coding: utf-8 -*-
"""
Holds all key chembl queries
"""
import logging
import sqlalchemy as sql
import pandas as pd
from mmp_kg import config
from mmp_kg.connectors.base_con import ChemDb

class MmpSqlDb(ChemDb):
    def __init__(self):
        self.name = self.source_name()

    @staticmethod
    def source_name():
        return 'mmpdb'

    def get_connection(path_to_db):
        connection = sql.create_engine(f'sqlite:///{path_to_db}')
        return connection

    def make_query(self, path_to_db, template: str, **kwargs):
        sql = query_template_dict[template](**kwargs)
    
        conn = self.get_connection(path_to_db)
        df = pd.read_sql_query(sql, conn)

        # Add details of query to the dataframe
        query_params = kwargs
        query_params['template'] = template
        df['query'] = str(query_params)
        df['source'] = self.name

        # Log
        logging.info(f'{len(df)}')

        return df
    
    @staticmethod
    def get_available_query_templates():
        return list(query_template_dict.keys())


def return_identity(x):
    return x

def get_fragment_nodes_2():
    """ get all assays for a single chembl document id"""
    query = '''SELECT DISTINCT t2.fragment_id as "fragmentid:ID(Fragment)", t2.smiles 
                             FROM
                             (SELECT re.environment_fingerprint_id, rs.smiles, rs.id as fragment_id
                             FROM rule_environment re
                             JOIN rule r ON re.rule_id = r.id
                             JOIN rule_smiles rs ON rs.id = r.from_smiles_id
                             UNION
                             SELECT re.environment_fingerprint_id, rs.smiles, rs.id as fragment_id
                             FROM rule_environment re
                             JOIN rule r ON re.rule_id = r.id
                             JOIN rule_smiles rs ON rs.id = r.to_smiles_id)t2'''
    return query

query_template_dict = {
    #Fragment nodes
    'get_fragment_nodes': lambda: '''SELECT DISTINCT t2.fragment_id as "fragmentid:ID(Fragment)", t2.smiles 
                                     FROM
                                     (SELECT re.environment_fingerprint_id, rs.smiles, rs.id as fragment_id
                                     FROM rule_environment re
                                     JOIN rule r ON re.rule_id = r.id
                                     JOIN rule_smiles rs ON rs.id = r.from_smiles_id
                                     UNION
                                     SELECT re.environment_fingerprint_id, rs.smiles, rs.id as fragment_id
                                     FROM rule_environment re
                                     JOIN rule r ON re.rule_id = r.id
                                     JOIN rule_smiles rs ON rs.id = r.to_smiles_id)t2''',
    #Compound nodes
    'get_compound_nodes': lambda: '''SELECT c.id as "compoundid:ID(Compound)", c.clean_smiles as smiles 
                                     FROM compound c''',
    #Environment nodes
    'get_environment_nodes': lambda: '''SELECT DISTINCT re.environment_fingerprint_id as "environmentid:ID(Environment)",  
                                        re.radius as "radius:int", 
                                        ef.fingerprint
                                        FROM rule_environment re
                                        JOIN environment_fingerprint ef ON re.environment_fingerprint_id = ef.id
                                        GROUP BY re.environment_fingerprint_id''',
    #Fragment -> Environment edges - IS_IN_ENVIRONMENT
    'get_fragment_environment_edges': lambda: '''SELECT DISTINCT t2.environment_fingerprint_id as ":END_ID(Environment)",
                                                 t2.id as ":START_ID(Fragment)"
                                                 FROM
                                                 (SELECT re.environment_fingerprint_id, rs.smiles, rs.id
                                                 FROM rule_environment re
                                                 JOIN rule r ON re.rule_id = r.id
                                                 JOIN rule_smiles rs ON rs.id = r.from_smiles_id
                                                 UNION
                                                 SELECT re.environment_fingerprint_id, rs.smiles, rs.id
                                                 FROM rule_environment re
                                                 JOIN rule r ON re.rule_id = r.id
                                                 JOIN rule_smiles rs ON rs.id = r.to_smiles_id)t2''',
    #Fragment -> Fragment - MMP_RULE_ENVIRONMENT
    'get_fragment_fragment_edges': lambda: '''SELECT r.from_smiles_id as ":START_ID(Fragment)",
                                              r.to_smiles_id as ":END_ID(Fragment)",
                                              res.id as "id:int",
                                              res.rule_environment_id as "rule_environment_id:int",
                                              res.property_name_id as "property_name_id:int",
                                              pn.name as "property_name",
                                              res.count as "count:int",
                                              res.avg as "avg:float",
                                              res.std as "std:float",
                                              res.kurtosis as "kurtosis:float",
                                              res.skewness as "skewness:float",
                                              res.min as "min:float",
                                              res.q1 as "q1:float",
                                              res.median as "median:float",
                                              res.max as "max:float",
                                              res.paired_t as "paired_t:float", 
                                              res.p_value as "p_value:float",
                                              re.environment_fingerprint_id as "environment_fingerprint_id:int",
                                              re.radius as "radius:int", ef.fingerprint
                                              FROM rule_environment_statistics res
                                              JOIN rule_environment re ON re.id = res.rule_environment_id
                                              JOIN rule r ON re.rule_id = r.id
                                              JOIN environment_fingerprint ef ON re.environment_fingerprint_id = ef.id
                                              JOIN property_name pn ON res.property_name_id = pn.id
                                              ORDER BY res.count desc''',
    #Compound <-> Compound - IS_MMP_OF
    'get_compound_compound_edges': lambda: '''SELECT DISTINCT c.compound1_id as ":START_ID(Compound)",
                                              c.compound2_id as ":END_ID(Compound)"
                                              FROM pair c
                                              JOIN compound AS cp1 ON cp1.id = c.compound1_id
                                              JOIN compound AS cp2 ON cp2.id = c.compound2_id''',
    #Compound -> Fragment - IS_FRAGMENT_OF
    'get_compound_fragment_edges': lambda: '''SELECT p.compound1_id as ":START_ID(Compound)", 
                                              r.from_smiles_id as ":END_ID(Fragment)"
                                              FROM pair p
                                              JOIN rule_environment re ON p.rule_environment_id = re.id
                                              JOIN rule r ON re.rule_id = r.id
                                              JOIN rule_smiles rs ON rs.id = r.from_smiles_id
                                              UNION
                                              SELECT p.compound2_id as "compound_id", r.to_smiles_id as "fragment_id"
                                              FROM pair p
                                              JOIN rule_environment re ON p.rule_environment_id = re.id
                                              JOIN rule r ON re.rule_id = r.id
                                              JOIN rule_smiles rs ON rs.id = r.to_smiles_id''',
    #Custom query
    'custom_query': lambda sql: return_identity(sql),
}