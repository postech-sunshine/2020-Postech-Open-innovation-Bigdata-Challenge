import tensorflow as tf
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard, ReduceLROnPlateau

mpl.rcParams['figure.figsize'] = (8, 6)
mpl.rcParams['axes.grid'] = False

# %%
tf.random.set_seed(10)
BATCH_SIZE = 32
BUFFER_SIZE = 10000
EPOCH = 5

# %%
past_history = 4 * 24 * 10
future_target = 4 * 24
STEP = 4
SHIFT_STEP = 1

# %%
def root_mean_squared_error_loss(y_true, y_pred):
    return tf.keras.backend.sqrt(tf.keras.losses.MSE(y_true, y_pred))

def xy_split(d, scale, y=True):
    d_trans = scale.transform(d)
    if y:
        d_x = d_trans[:,1:]
        d_y = d_trans[:, 0]
        d_x = d_x.reshape((d_x.shape[0], 1, d_x.shape[1]))
        return d_x, d_y
    if not y:
        d_x = d_trans[:,1:]
        d_x = d_x.reshape((d_x.shape[0], 1, d_x.shape[1]))
        return d_x


tf.random.set_seed(42)
raw_df = pd.read_csv("../../data/datefrom1st_revised.csv")
raw_df.index = raw_df.datetime

df = raw_df
df = df.drop(
    ["Unnamed: 0", 'datetime', 'percipitation', 'air_pressure', 'sea_level_pressure',
     'wind_degree'], axis=1)
df["difference"] = df.astype('int32')

df.drop(df.loc[(df.index > '2020-01-31 00:00:00') & (df.index < '2020-02-01 00:00:00')].index, inplace=True)
df.drop(df.loc[(df.index > '2020-03-31 00:00:00') & (df.index < '2020-04-01 00:00:00')].index, inplace=True)
df.drop(df.loc[(df.index > '2020-05-31 00:00:00') & (df.index < '2020-06-01 00:00:00')].index, inplace=True)
df = df.fillna(0)
ult = df.loc["2020-01-24 00:00:00":"2020-01-31 00:00:00"]
final_test = df.loc["2020-05-30 00:00:00":"2020-05-30 23:45:00"]
df = df.loc[:"2020-05-30 00:00:00"]

# %%

TRAIN_SPLIT = int(len(df.index) * 0.8)
scaler = MinMaxScaler().fit(df)
values = scaler.transform(df)



train = values[:TRAIN_SPLIT, :]
test = values[TRAIN_SPLIT:, :]


# split into input and outputs
train_X, train_y = xy_split(train, scaler)
test_X, test_y = xy_split(test, scaler)
ult_X, ult_y = xy_split(ult, scaler)
final_test_X, final_test_y = xy_split(final_test, scaler)

# %%x
def plot_train_history(history, title):
    loss = history.history['loss']
    val_loss = history.history['val_loss']

    epochs = range(len(loss))

    plt.figure()

    plt.plot(epochs, loss, 'b', label='Training loss')
    plt.plot(epochs, val_loss, 'r', label='Validation loss')
    plt.title(title)
    plt.legend()

    plt.show()


# %%

def show_plot(plot_data, delta, title):
    labels = ['History', 'True Future', 'Model Prediction']
    marker = ['.-', 'rx', 'go']
    time_steps = create_time_steps(plot_data[0].shape[0])
    if delta:
        future = delta
    else:
        future = 0

    plt.title(title)
    for i, x in enumerate(plot_data):
        if i:
            plt.plot(future, plot_data[i], marker[i], markersize=10,
                     label=labels[i])
        else:
            plt.plot(time_steps, plot_data[i].flatten(), marker[i], label=labels[i])
    plt.legend()
    plt.xlim([time_steps[0], (future + 5) * 2])
    plt.xlabel('Time-Step')
    return plt


def create_time_steps(length):
    return list(range(-length, 0))


# %%

def multi_step_plot(history, true_future, prediction):
    plt.figure(figsize=(12, 6))
    num_in = create_time_steps(len(history))
    num_out = len(true_future)

    plt.plot(num_in, np.array(history[:, 1]), label='History')
    plt.plot(np.arange(num_out) / STEP, np.array(true_future), 'bo',
             label='True Future')
    if prediction.any():
        plt.plot(np.arange(num_out) / STEP, np.array(prediction), 'ro',
                 label='Predicted Future')
    plt.legend(loc='upper left')
    plt.show()
    plt.savefig("output.png")


# %%

def fit_by_batch(X, y, batch_size):
    n_batches_for_epoch = X.shape[0]//batch_size
    for i in range(n_batches_for_epoch):
        index_batch = range(X.shape[0])[batch_size*i:batch_size*(i+1)]
        X_batch =X[index_batch][0].toarray()[0] #from sparse to array
        X_batch=X_batch.reshape(1,X_batch.shape[0],1 ) # to 3d array
        y_batch = y[index_batch,][0]
        yield(np.array(X_batch),y_batch)


print(train_X.shape)
import tensorflow as tf

# %%
from tensorflow.keras.utils import multi_gpu_model
from tensorflow.python.client import device_lib

EVALUATION_INTERVAL = 200


def get_available_gpus():
    local_device_protos = device_lib.list_local_devices()
    return [x.name for x in local_device_protos if x.device_type == 'GPU']


def get_gpu_num():
    return len(get_available_gpus())


path_checkpoint = '../23_checkpoint.keras'
callback_checkpoint = ModelCheckpoint(filepath=path_checkpoint,
                                      monitor='val_loss',
                                      verbose=1,
                                      save_weights_only=True,
                                      save_best_only=True)

callback_early_stopping = EarlyStopping(monitor='val_loss', patience=80, verbose=1)

callback_tensorboard = TensorBoard(log_dir='../23_logs/', histogram_freq=0, write_graph=False)
callback_reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, min_lr=1e-7, patience=10,verbose=1)
callbacks = [callback_early_stopping, callback_checkpoint, callback_tensorboard, callback_reduce_lr]





multi_step_model = tf.keras.models.Sequential()
multi_step_model.add(tf.keras.layers.GRU(350, activation="relu",  return_sequences=True, input_shape=(train_X.shape[1], train_X.shape[2])))
multi_step_model.add(tf.keras.layers.GRU(350, activation="relu", return_sequences=True))
multi_step_model.add(tf.keras.layers.Dense(1))





print(f"[+] Available GPUs")
print(get_available_gpus())

if get_gpu_num() < 2:
    print(f"[+] Available multiple GPU not found... Just use CPU! XD")
else:
    print(f"[+] {get_gpu_num()} GPUs found! Setting to GPU model...")
    multi_step_model = multi_gpu_model(multi_step_model, gpus=get_gpu_num())

multi_step_model.compile(optimizer=tf.keras.optimizers.Adam(lr=0.001), loss='mse')

history = multi_step_model.fit(train_X, train_y, epochs=EPOCH, batch_size=BATCH_SIZE, validation_data=(test_X, test_y),
                               verbose=2, shuffle=True, callbacks=callbacks)

try:
    multi_step_model.load_weights(path_checkpoint)
except Exception as error:
    print("Error trying to load checkpoint.")
    print(error)
#
# # plot history
# pyplot.plot(history.history['loss'], label='train')
# pyplot.plot(history.history['val_loss'], label='test')
# pyplot.legend()
# pyplot.show()
# pyplot.savefig("test.png")

# %%

from numpy import concatenate
from math import sqrt
from sklearn.metrics import mean_squared_error


def make_prediction(model, X, y, plot_name):
    yhat = model.predict(X)[:, :, 0]
    X_revert = X.reshape((X.shape[0], X.shape[2]))
    inv_yhat = concatenate((yhat, X_revert), axis = 1)
    inv_xyhat = scaler.inverse_transform(inv_yhat)
    inv_yhat = inv_xyhat[:, 0]
    print("inv_yhat shape {}".format(inv_yhat.shape))
    y_revert = y.reshape((len(y), 1))
    inv_y1 = concatenate((y_revert, X_revert), axis = 1)
    print("after concate: {}".format(inv_y1.shape))
    inv_y1 = scaler.inverse_transform(inv_y1)
    inv_y = inv_y1[:, 0]
    print(inv_y.shape)
    rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
    print('Test RMSE: %.6f' % rmse)
    print('Test MAE: %.6f' % mean_squared_error(inv_y, inv_yhat))


    fig = plt.figure
    plt.plot(inv_y, 'b', label = 'true')
    plt.plot(inv_yhat, 'g', label = 'pred')
    plt.legend()
    plt.savefig(plot_name)

print(final_test_X.shape)
make_prediction(multi_step_model, final_test_X, final_test_y, "final_test.png")

# %%
#2017 8 3
y = 17
date =3
idx = 3
base = pd.read_csv("../../data/future/SURFACE_ASOS_131_MI_2017-08_2017-08_2017.csv", encoding='euc-kr').fillna(0)
base.columns

base = base[['일시', '기온(°C)','풍속(m/s)', '습도(%)','일사(MJ/m^2)','일조(Sec)']]
base = base.rename(columns={'일시':'datetime', '기온(°C)':"temperature",'풍속(m/s)':"wind_speed", '습도(%)':"humidity",
                            "일조(Sec)":"solar_radiation",'일사(MJ/m^2)':"solar_intensity"
})
base.datetime = pd.to_datetime(base.datetime, infer_datetime_format=True)
base["difference"] = base["datetime"].sub(pd.to_datetime("2017-01-01", infer_datetime_format=True), axis=0)/ np.timedelta64(1, 'D')

base = base.set_index('datetime')
base = base[f"20{y}-08-0{date} 00:00":f"20{y}-08-0{date} 23:59"]




#%%
out = pd.DataFrame()
period_min = 15
out["result"] = 0
out["temperature"] = base["temperature"].resample(f'{str(period_min)}T').mean()
out["wind_speed"] = base["wind_speed"] .resample(f'{str(period_min)}T').mean()
out["humidity"]= base["humidity"].resample(f'{str(period_min)}T').mean()
out["solar_intensity"] = base["solar_intensity"].resample(f'{str(period_min)}T').mean().diff()
out["solar_radiation"] = base["solar_radiation"].resample(f'{str(period_min)}T').mean().diff()
out["date"] = 31
out["month"] = 7
out["hour"] = pd.DatetimeIndex(out.index).hour
out["difference"] = base["difference"]
out.loc[out["solar_intensity"] < 0 , "solar_intensity"] = 0
out.loc[out["solar_radiation"] < 0 , "solar_radiation"] = 0
out = out.fillna(0)
out_X, out_y = xy_split(out, scaler)
make_prediction(multi_step_model, out_X, out_y, "final_test.png")