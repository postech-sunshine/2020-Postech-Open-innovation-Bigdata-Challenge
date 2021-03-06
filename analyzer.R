setwd("~/Github/2020-Postech-Open-innovation-Bigdata-Challenge")


# import daily weather data
importWeather <- function(){
  data_t_n<-read.csv(file="data/daily_temperatures_national.csv",stringsAsFactors=FALSE)
  data_t_p<-read.csv(file="data/daily_temperatures_pohang.csv",stringsAsFactors=FALSE)
  data_t_s<-read.csv(file="data/daily_temperatures_seoul.csv",stringsAsFactors=FALSE)

  data_p_n<-read.csv(file="data/daily_precipitation_national.csv",stringsAsFactors=FALSE)
  data_p_p<-read.csv(file="data/daily_precipitation_pohang.csv",stringsAsFactors=FALSE)
  data_p_s<-read.csv(file="data/daily_precipitation_seoul.csv",stringsAsFactors=FALSE)
  
  data_t<-rbind(data_t_n, data_t_p, data_t_s)
  data_p<-rbind(data_p_n, data_p_p, data_p_s)
  #data_p[is.na(data_p)] <- 0
  
  data <- merge(data_t, data_p, by=c("날짜","지점"))
  names(data) <- c("date","location","avgTemp","minTemp","maxTemp","precipitation")
  data$date<-as.Date(data$date)
  return(data)
}

# import electrical energy(generated by Solar PV) data (unit : kWh)
importEnergy <- function(){
  data <- read.csv(file="data/SolarPV_Elec_Problem.csv",header=F,stringsAsFactors=FALSE)
  names(data) <- c("datetime","amount")
  data$date<-as.Date(data$datetime)
  data["datetime"]<-sapply(data["datetime"], function(x) as.POSIXlt(x,format="%Y-%m-%dT%H:%M:%S+09:00",tz="Asia/Seoul"))
  data$time<-as.integer(format(data$datetime,"%H"))+as.integer(format(data$datetime,"%M"))/15*0.25
  return(data)
}


weather <- importWeather()
energy <- importEnergy()
data <- merge(weather, energy, by="date")


data_national <- data[data$location == "전국",]
attach(data_national)

par(mfrow=c(2,1))
hist(precipitation[precipitation>0], breaks = 30, col = "lightblue", main="Histogram of precipitation")
hist(amount[amount>0], breaks = 30, col = "green", main="Histogram of Amount" )

library(scatterplot3d)
par(mfrow=c(1,1))
scatterplot3d(date, time, amount, highlight.3d=TRUE, col.axis="blue", col.grid="lightblue", main="date-time-amount", pch=20)

data_national_precipZero <- data_national[precipitation == 0,]
attach(data_national_precipZero)
scatterplot3d(avgTemp, time, amount, highlight.3d=TRUE, col.axis="blue", col.grid="lightblue", main="avgTemp-time-amount", pch=20)
