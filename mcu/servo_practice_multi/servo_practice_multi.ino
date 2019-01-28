# This project uses the Texas Instruments MSP432P401R Development Board
# For the servo motors, MG996R were used with their individual power supplies
# As for the spaghetti code, chill-out! This is just for demo!

#include "msp432.h"
#include "driverlib.h"
#include <Servo.h>
#undef LED
#define LED GREEN_LED

// Status LED Variables
const unsigned long STATUS_DURATION = 2000;
unsigned long statusLEDTimeoutLimit = millis();
bool lightOn = FALSE;

// Servo Variables
Servo myservo0, myservo1, myservo2;  // create servo object with maximum of eight servo objects allowed
const int servoPin0 =  40; // Pin P2_7
const int servoPin1 =  39; // Pin P2_6
const int servoPin2 =  38; // Pin P2_4
const int SERVO_STEP = 40;
const int POS_MAX = 40;
const int POS_MIN = 0;
int pos0 = POS_MIN; // variable to store the servo position
int pos1 = POS_MIN;
int pos2 = POS_MIN;
const int CLOSED = 0;
const int OPENING = 1;
const int OPENED = 2;
const int CLOSING = 3;
int lid0Status = CLOSED;
int lid1Status = CLOSED;
int lid2Status = CLOSED;
const unsigned long SERVO_DELAY = 10;
const unsigned long OPEN_DURATION = 2500;
unsigned long servo0TimeMark = millis();
unsigned long servo1TimeMark = millis();
unsigned long servo2TimeMark = millis();


void setup(){
  pinMode(LED, OUTPUT);
  myservo0.attach(servoPin0);  // attaches the servo on Port F, pin 1 (Red LED pin) to the servo object
  myservo1.attach(servoPin1);  // attaches the servo on Port F, pin 1 (Red LED pin) to the servo object
  myservo2.attach(servoPin2);  // attaches the servo on Port F, pin 1 (Red LED pin) to the servo object
  myservo0.write(POS_MIN);
  myservo1.write(POS_MIN);
  myservo2.write(POS_MIN);
  Serial.begin(9600);
  // Say Hello!
  digitalWrite(LED, HIGH);
  delay(2000);
  digitalWrite(LED, LOW);
}

 
void loop(){ 
  handleSerial();
  statusLight();
  operateServo0();
  operateServo1();
  operateServo2();
}    

void handleSerial() {
  if (Serial.available() > 0) {
    char incomingCharacter = Serial.read();
    switch (incomingCharacter) {
      case '0':
        lightOn = TRUE;
        statusLEDTimeoutLimit = millis();
        break;
      case '1':
        lid0Status = OPENING;
        servo0TimeMark = millis();
        break;
      case '2':
        lid1Status = OPENING;
        servo1TimeMark = millis();
        break;
      case '3':
        lid0Status = OPENING;
        servo0TimeMark = millis();
        lid1Status = OPENING;
        servo1TimeMark = millis();
        break;
      case '4':
        lid2Status = OPENING;
        servo2TimeMark = millis();
        break;
      case '5':
        lid1Status = OPENING;
        servo1TimeMark = millis();
        lid2Status = OPENING;
        servo2TimeMark = millis();
        break;
      case '6':
        lid0Status = OPENING;
        servo0TimeMark = millis();
        lid2Status = OPENING;
        servo2TimeMark = millis();
        break;
      case '7':
        lid0Status = OPENING;
        servo0TimeMark = millis();
        lid1Status = OPENING;
        servo1TimeMark = millis();
        lid2Status = OPENING;
        servo2TimeMark = millis();
        break;     
    }
    
  }
}


void operateServo0(){
  if(CLOSED == lid0Status){
    // do nothing
    pos0 = POS_MIN; // just to be sure
  } else if (OPENING == lid0Status){
    if(pos0 >= POS_MAX){
      lid0Status = OPENED;
      servo0TimeMark = millis(); // reset timer for lid open duration
    } else{
      if(millis() - servo0TimeMark > SERVO_DELAY){
        pos0 += SERVO_STEP;
        myservo0.write(min(pos0, POS_MAX));
        servo0TimeMark = millis();
      }
    }
  } else if (OPENED == lid0Status){
    pos0 = POS_MAX; // just to be sure
    if(millis() - servo0TimeMark > OPEN_DURATION){
      lid0Status = CLOSING;
    }
  } else if (CLOSING == lid0Status){
    if(pos0 <= POS_MIN){
      lid0Status = CLOSED;
    } else{
      if(millis() - servo0TimeMark > SERVO_DELAY){
        pos0 -= SERVO_STEP;
        myservo0.write(max(pos0, POS_MIN));
        servo0TimeMark = millis();
      }
    }
  }
}


void operateServo1(){
  if(CLOSED == lid1Status){
    // do nothing
    pos1 = POS_MIN; // just to be sure
  } else if (OPENING == lid1Status){
    if(pos1 >= POS_MAX){
      lid1Status = OPENED;
      servo1TimeMark = millis(); // reset timer for lid open duration
    } else{
      if(millis() - servo1TimeMark > SERVO_DELAY){
        pos1 += SERVO_STEP;
        myservo1.write(min(pos1, POS_MAX));
        servo1TimeMark = millis();
      }
    }
  } else if (OPENED == lid1Status){
    pos1 = POS_MAX; // just to be sure
    if(millis() - servo1TimeMark > OPEN_DURATION){
      lid1Status = CLOSING;
    }
  } else if (CLOSING == lid1Status){
    if(pos1 <= POS_MIN){
      lid1Status = CLOSED;
    } else{
      if(millis() - servo1TimeMark > SERVO_DELAY){
        pos1 -= SERVO_STEP;
        myservo1.write(max(pos1, POS_MIN));
        servo1TimeMark = millis();
      }
    }
  }
}


void operateServo2(){
  if(CLOSED == lid2Status){
    // do nothing
    pos2 = POS_MIN; // just to be sure
  } else if (OPENING == lid2Status){
    if(pos2 >= POS_MAX){
      lid2Status = OPENED;
      servo2TimeMark = millis(); // reset timer for lid open duration
    } else{
      if(millis() - servo2TimeMark > SERVO_DELAY){
        pos2 += SERVO_STEP;
        myservo2.write(min(pos2, POS_MAX));
        servo2TimeMark = millis();
      }
    }
  } else if (OPENED == lid2Status){
    pos2 = POS_MAX; // just to be sure
    if(millis() - servo2TimeMark > OPEN_DURATION){
      lid2Status = CLOSING;
    }
  } else if (CLOSING == lid2Status){
    if(pos2 <= POS_MIN){
      lid2Status = CLOSED;
    } else{
      if(millis() - servo2TimeMark > SERVO_DELAY){
        pos2 -= SERVO_STEP;
        myservo2.write(max(pos2, POS_MIN));
        servo2TimeMark = millis();
      }
    }
  }
}


void statusLight(){
  if(lightOn){
    digitalWrite(LED, HIGH);
    if(millis() - statusLEDTimeoutLimit > STATUS_DURATION){
      lightOn = FALSE;
    }
  } else{
    digitalWrite(LED, LOW);
  }
}

//
//void statusLight(){
//  if(lightOn){
//    digitalWrite(LED, HIGH);
//    if(millis() - statusLEDTimeoutLimit > STATUS_DURATION){
//      lightOn = FALSE;
//      digitalWrite(LED, LOW);
//    }
//  }
//}

//
//    if(data == '3'){
//      for(pos = 0; pos < 80; pos += 1){  // goes from 0 degrees to 80 degrees in steps of 1 degree
//        myservo0.write(pos);              // tell servo to go to position in variable 'pos' 
//        myservo1.write(pos);
//        myservo2.write(pos);
//        delay(10);                       // waits 15ms for the servo to reach the position 
//      } 
//      delay(2500);
//      for(pos = 80; pos>=1; pos-=1){     // goes from 80 degrees to 0 degrees 
//        myservo0.write(pos);              // tell servo to go to position in variable 'pos' 
//        myservo1.write(pos);
//        myservo2.write(pos);
//        delay(10);                       // waits 15ms for the servo to reach the position 
//      }
//    }
