import pickle
import datetime
import math
import pandas as pd
import numpy as np
import inflection




class Rossmann( object ):
    def __init__( self ):
        self.home_path=''
        self.competition_distance_scaler = pickle.load( open( self.home_path + 'competition_distance_scaler.pkl', 'rb') )
        self.competition_time_month_scaler = pickle.load( open( self.home_path + 'competition_time_month_scaler.pkl', 'rb') )
        self.promo_time_week_scaler = pickle.load( open( self.home_path + 'promo_time_week_scaler.pkl', 'rb') )
        self.year_scaler = pickle.load( open( self.home_path + 'year_scaler.pkl', 'rb') )
        self.store_type_scaler = pickle.load( open( self.home_path + 'store_type_scaler.pkl', 'rb') )
        
    def data_cleaning( self, df1 ):
        #3.1 Renomear Colunas
        old_cols = ['Store', 'DayOfWeek', 'Date', 'Open', 'Promo','StateHoliday', 'SchoolHoliday',
        'StoreType', 'Assortment', 'CompetitionDistance','CompetitionOpenSinceMonth',
        'CompetitionOpenSinceYear', 'Promo2', 'Promo2SinceWeek','Promo2SinceYear', 'PromoInterval']
        snakecase = lambda x: inflection.underscore(x)
        new_cols = list(map(snakecase, old_cols))
        df1.columns = new_cols
        
        #Convertendo data
        df1['date'] = pd.to_datetime(df1['date'])
        
        #3.3 Preenchimento dos NA
        #competition_distance: A premissa adotada é que  não existem competidores próximos da loja, de forma que substituiremos 
        #os valores NA por valores muito altos
        df1['competition_distance'] = df1['competition_distance'].apply(lambda x: 200000.00 if pd.isna(x) else x)

        #competition_open_since_month: A premissa adotada é manter as linhas NA, porém usar o mês da venda daquela loja como data da
        # abertura da concorrente.
        df1['competition_open_since_month'] = df1.apply(lambda x: x['date'].month if pd.isna(x['competition_open_since_month']) else x['competition_open_since_month'], axis=1)

        #competition_open_since_year: A premissa adotada é manter as linhas NA, porém usar o mês da venda daquela loja como data da
        # abertura da concorrente.
        df1['competition_open_since_year'] = df1.apply(lambda x: x['date'].year if pd.isna(x['competition_open_since_year']) else x['competition_open_since_year'], axis=1)

        #promo2_since_week 
        df1['promo2_since_week'] = df1.apply(lambda x: x['date'].week if pd.isna(x['promo2_since_week']) else x['promo2_since_week'], axis=1)

        #promo2_since_year           
        df1['promo2_since_year'] = df1.apply(lambda x: x['date'].year if pd.isna(x['promo2_since_year']) else x['promo2_since_year'], axis=1)

        #promo_interval
        month_map = {1:'Jan',2:'Fev',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
        df1['promo_interval'].fillna(0, inplace = True)
        df1['month_map'] = df1['date'].dt.month.map(month_map)
        df1['is_promo_2'] = df1[['promo_interval', 'month_map']].apply(lambda x: 0 if x['promo_interval'] == 0 else 1 if x['month_map'] in x['promo_interval'].split(',') else 0, axis=1)
        
        #Convertendo tipo de dado
        df1['competition_open_since_month'] = df1['competition_open_since_month'].astype(int)
        df1['competition_open_since_year'] = df1['competition_open_since_year'].astype(int)
        df1['promo2_since_week'] = df1['promo2_since_week'].astype(int)
        df1['promo2_since_year'] = df1['promo2_since_year'].astype(int)
        
        return df1
    
    def feature_engineering( self, df2 ):
        #year
        df2['year'] = df2['date'].dt.year

        #month
        df2['month'] = df2['date'].dt.month

        #day
        df2['day'] = df2['date'].dt.day

        #week_of_year
        df2['week_of_year'] = df2['date'].dt.isocalendar().week

        #year_week
        df2['year_week'] = df2['date'].dt.strftime("%Y-%W")

        #competition_since
        df2['competition_since'] = df2.apply( lambda x: datetime.datetime(year=x['competition_open_since_year'],month=x['competition_open_since_month'],day=1 ), axis=1 )
        df2['competition_time_month'] = ( ( df2['date'] - df2['competition_since'] )/30).apply( lambda x: x.days ).astype( int )

        #promo2_since
        df2['promo2_since'] = df2['promo2_since_year'].astype( str ) + '-' + df2['promo2_since_week'].astype( str )
        df2['promo2_since'] = df2['promo2_since'].apply( lambda x: datetime.datetime.strptime( x + '-1', '%Y-%W-%w' ) - datetime.timedelta( days=7 ) )
        df2['promo_time_week'] = ( ( df2['date'] - df2['promo2_since'] )/7 ).apply(lambda x: x.days ).astype( int )

        #assortment
        df2['assortment'] = df2['assortment'].apply( lambda x: 'basic' if x == 'a' else 'extra' if x == 'b' else 'extended' )

        #state_holiday
        df2['state_holiday'] = df2['state_holiday'].apply( lambda x: 'public_holiday' if x == 'a' else 'easter_holiday' if x == 'b' else 'christmas' if x == 'c' else 'regular_day' )

        #season
        spring = range(79, 172)
        summer = range(172, 266)
        fall = range(266, 355)
        df2['season'] = df2['date'].apply(lambda x: 'spring' if x.timetuple().tm_yday in spring else 'summer' if x.timetuple().tm_yday in summer else 'fall' if x.timetuple().tm_yday in fall else 'winter' )
        
        ## 5.0 Filtragem de Variáveis 
        #Filtrando linhas onde a loja está fechada e também onde as vendas foram 0
        df2 = df2[(df2['open'] != 0)]
        
        #Filtrando colunas que não teremos no momento da previsão ou que foram colunas auxiliares na criação de váriaveis
        df2 = df2.drop(['open','promo_interval','month_map'], axis=1)
        
        return df2
    
    def data_preparation( self, df5 ):
        ### 7.2 Rescaling
        # competition distance
        df5['competition_distance'] = self.competition_distance_scaler.fit_transform(df5[['competition_distance']].values)

        # competition time month
        df5['competition_time_month'] = self.competition_time_month_scaler.fit_transform(df5[['competition_time_month']].values)

        # promo time week
        df5['promo_time_week'] = self.promo_time_week_scaler.fit_transform(df5[['promo_time_week']].values)

        # year
        df5['year'] = self.year_scaler.fit_transform(df5[['year']].values)
        
        #### 7.3.1 Encoding
        #state_holiday - one hot encoding
        df5 = pd.get_dummies(df5,prefix='state_holiday',columns=['state_holiday'])
        
        #store_type - label encoding
        df5['store_type'] = self.store_type_scaler.fit_transform(df5['store_type'])
        
        #assortment -ordinal encoding
        mapping = {"basic": 1,  "extra": 2, "extended": 3}
        df5['assortment'] = df5['assortment'].map(mapping)
        
        #season - ordinal encoding
        mapping2 = {"winter": 1,  "spring": 2, "summer": 3, 'fall': 4}
        df5['season'] = df5['season'].map(mapping2)
        
        #### 7.3.3 Transformação de Natureza
        # day_of_week
        df5['day_of_week_sin'] = df5['day_of_week'].apply( lambda x: np.sin( x * ( 2. *np.pi/7 )))
        df5['day_of_week_cos'] = df5['day_of_week'].apply( lambda x: np.cos( x * ( 2. *np.pi/7 )))

        # month
        df5['month_sin'] = df5['month'].apply( lambda x: np.sin( x * ( 2. * np.pi/12 )))
        df5['month_cos'] = df5['month'].apply( lambda x: np.cos( x * ( 2. * np.pi/12 )))

        # day
        df5['day_sin'] = df5['day'].apply( lambda x: np.sin( x * ( 2. * np.pi/30 )))
        df5['day_cos'] = df5['day'].apply( lambda x: np.cos( x * ( 2. * np.pi/30 )))

        # week_of_year
        df5['week_of_year_sin'] = df5['week_of_year'].apply( lambda x: np.sin( x * (2.*np.pi/52 )))
        df5['week_of_year_cos'] = df5['week_of_year'].apply( lambda x: np.cos( x * (2.*np.pi/52 )))

        # season
        df5['season_sin'] = df5['season'].apply( lambda x: np.sin( x * (2.*np.pi/4 )))
        df5['season_cos'] = df5['season'].apply( lambda x: np.cos( x * (2.*np.pi/4 )))
        
        cols_selected_boruta = ['store','promo','store_type','assortment','competition_distance','competition_open_since_month','competition_open_since_year',
                         'promo2','promo2_since_week','promo2_since_year','competition_time_month','promo_time_week','day_of_week_sin','day_of_week_cos',
                         'month_cos','month_sin','day_sin','day_cos','week_of_year_sin','week_of_year_cos']
        
        return df5[ cols_selected_boruta ]
    
    def get_prediction( self, model, original_data, test_data ):
        # Previsão
        pred = model.predict( test_data )
        
        # Colocando a previsão no dataframe original
        original_data['prediction'] = np.expm1( pred )
        
        return original_data.to_json( orient='records', date_format='iso' )