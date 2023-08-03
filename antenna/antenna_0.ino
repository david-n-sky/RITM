# define dirPin  6
# define stepPin  7
# define en  8  // en - пин отключения драйвера
# define sens_start_position  2  // пин датчика крайнего положения
# define start_impulse  3  // пин, с которого идет импульс

//Настройки
int big_step_count = 3600; //Количество десятичных шагов в длине рейки
int motor_speed = 70; //Скорость перемещения
int pos_inv_time = 3; //Минимальное время инвентаризации в одном положении, сек
int pos_run_time = 2; //Максимальное время перемещения из одного положения в другое, сек
int all_steps = 18500;  // Всего шагов в рейке

//Вычисляемые параметры
uint32_t time_duration_count = 30; //Время инвентаризации
int pos_count = 5; //Количество остановок
int pos_distance = 3700; //Расстояние между положениями
int center_coordinate; // Координата центрального положения

volatile boolean flag_run = false;
//int PIN_BUTTON = 3;

void setup() 
{
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(en, OUTPUT);
  pinMode(sens_start_position, INPUT);
  pinMode(start_impulse, INPUT);
  //pinMode(PIN_BUTTON, OUTPUT);
  //pinMode(13, OUTPUT);
  
  //digitalWrite(PIN_BUTTON, HIGH);
  digitalWrite(en, HIGH); 
  
  attachInterrupt(1, readTimeDuration, RISING);

  center_coordinate = (pos_count / 2) * pos_distance;
  //pos_distance = all_steps / pos_count;
}


void readTimeDuration() //прерывание
{
  flag_run=true;
}


void onePositionInvenory(boolean dir) //смена позиции
{ 
  for(int x = 0; x < pos_distance; x++)
  {  
    digitalWrite(en, LOW);
    digitalWrite(dirPin, dir);
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(motor_speed);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(motor_speed);
  }
  digitalWrite(en, HIGH);
  delay (3000);
}

void returnAnt() // возвращение антенны в стартовую позицию
{
  while (!digitalRead(sens_start_position))
  {
    digitalWrite(en, LOW);
    digitalWrite(dirPin, LOW);
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(motor_speed);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(motor_speed);
    digitalWrite(en,HIGH );
  }
}

void center(boolean dir){
  for(int x = 0; x < center_coordinate; x++)
  {  
    digitalWrite(en, LOW);
    digitalWrite(dirPin, dir);
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(motor_speed);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(motor_speed);
  }
  digitalWrite(en, HIGH);
}


void loop() 
{
  if (flag_run)
  {
    flag_run = false;
    returnAnt();
    int i = 0;
    delay(pos_inv_time*1000);
    while (i < pos_count)
    {
      if (flag_run){
        break;
      }
      delay(1000);
      onePositionInvenory(HIGH);
      i++;
    }
    if (!flag_run){
      center(LOW);
    }
  }
}
  
