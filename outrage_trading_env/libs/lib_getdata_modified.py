import pandas as pd
import numpy as np
import sklearn.model_selection as sklms

#was removed the function 'get_data' due the requeriment to MetaTrader5 library

def ravel(splited_datax):
    datax=splited_datax
    for i in range(0,datax.__len__(),1):
        datax[i]=datax[i].to_numpy()
        datax[i]=np.ravel(datax[i])
    return datax

def evalmodel(model,datax,datay,kfold_num=10,verbose=False,metric='f1',n_jobs=-1):
    crossval=sklms.cross_validate(model,datax,datay,cv=kfold_num,verbose=verbose,n_jobs=n_jobs,scoring=metric)
    model_value=0
    for i in range(0,list(crossval['test_score']).__len__(),1):
        model_value+=crossval['test_score'][i]
    result=(model_value/list(crossval['test_score']).__len__())
    return result


def dataframe_transform(datax,columnstoexclude=None,renamecolumns={'time':'Time','open':'Open','high':'High','low':'Low','close':'Close','tick_volume':'Volume','spread':'Spread'}):
    '''
    transforma as amostras em um dataframe. o parametro columns to exclude pode ser usado pra excluir uma coluna do dataframe
    params:
    -------
    datax: o datax timeseries lista ou turple
    columnstoexclude: lista de strings (nomes das colunas) o nome deve ser o nome antes do rename
    renamecolumns: dict renomeia as colunas, chave e valor
    '''
    datax=datax
    datax=pd.DataFrame(datax)
    #com spread #0.5
    #sem spread #0.49
    if columnstoexclude!=None:
        datax=datax.drop(columns=list(columnstoexclude))
    datax=datax.rename(columns=renamecolumns)
    return datax

def split_into_samples(data_dataframe,number_of_samples='auto',bars_per_sample=64):
    '''
    divide o dataframe em partes
    '''
    datax=data_dataframe
    if number_of_samples=='auto':
        number_of_samples=int(round(datax.index.size/bars_per_sample,0))
    samples=[]
    for i in range(0,number_of_samples,1):
        samples.insert(i,np.nan)
        try:
            samples[i]=datax.loc[(samples.__len__()-1)*bars_per_sample:((samples.__len__()-1)*bars_per_sample+bars_per_sample)-1]
        except:
            raise Exception("the maximum number of samples is: "+str(round(datax.index.size/bars_per_sample,0)))
        if samples[i].__len__()!=bars_per_sample:
            samples.pop(i)
    return samples

def label_simple(sampled_datax,distance_to_predict=32):
    '''
    gera o datay para a data, retorna o novo datax e datay.

    Return:
    -------
        return [datax,datay]
    '''
    datax=sampled_datax
    result=[]
    for i in range(0,datax.__len__()-1,1):
        if datax[i+1]['Close'].iloc[distance_to_predict-1]>datax[i]['Close'].iloc[-1]:
            result.append([1])
        else:
            result.append([-1])
    return [datax[:-1],result]

def label_direction_number_bars(sampled_datax,distance_to_predict=32):
    '''
    Return:
    -------
        [datax,datay]
    '''
    datax=sampled_datax
    analisis=[]
    analisis_to_result=0
    result=[]
    for i in range(0,datax.__len__()-1,1):
        analisis.append(datax[i+1]['Close'].iloc[:distance_to_predict-1])
        for h in range(0,analisis[-1].index.size-1,1):
            if analisis[-1].iloc[h+1]>analisis[-1].iloc[h]:
                analisis_to_result+=1
            else:
                analisis_to_result-=1
        result.append([analisis_to_result])
        analisis_to_result=0
    return [datax[:-1],result]

def label_interaction_simple_direction_number_bars(datay_simple,datay_direction_number_bars,threshold=1):
    if list(datay_simple).__len__()!=list(datay_direction_number_bars).__len__():
        raise Exception("there a difference between number of indexes among datay_simple and datay_direction_number_bars")
    datay_simple=datay_simple
    datay_advanced=datay_direction_number_bars
    result=[]
    threshold=threshold
    for i in range(0,datay_simple.__len__() if datay_simple.__len__()==datay_advanced.__len__() else datay_advanced,1):
        if datay_simple[i]==[1] and datay_advanced[i]>=[threshold]:
            result.append([1])
        elif datay_simple[i]==[-1] and datay_advanced[i]<=[-threshold]:
            result.append([-1])
        elif datay_simple[i]==[1] and datay_advanced[i]<[0]:
            result.append([99])
        elif datay_simple[i]==[-1] and datay_advanced[i]>[0]:
            result.append([99])
        else:
            result.append([0])
    return result