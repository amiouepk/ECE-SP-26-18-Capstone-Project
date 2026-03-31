// Talks to multiple BNO085 sensors through a TCA9548 multiplexer.
//
// Uses NED/aerospace coordinates, so my axes definitions may differ from your other projects.
// Outputs data in compact Base64 format.
//
// Uses frustrating deficient Wire I2C library. Must do time-consuming SHTP header rereads, hurting overall performance.
// Need a better I2C library that allows reading an unlimited length I2C message one byte at a time without forcing any STOP/START cycles midway, because BNO085 message length is determined by bytes within the message.
//
// To improve SDA-to-SCL setup time during clock-stretching cycles, try adding a 2.7K pullup to SDA and a 4.7K pullup to SCL (or similar values), and use short I2C wires (a few cm).
//
// I measure 700us I2C clock stretching cycles. Ouch! Hillcrest, please try harder to reduce or eliminate clock stretching.
//
// To program Adafruit Feather M4 Express 3857:  select "Adafruit Feather M4 Express (SAMD51)", COMxx, "AVRISP mkII". Beware COM port may annoyingly change itself.
// To program Adafruit Metro Mini 2590:  select "Adafruit Metro", COMxx, "AVRISP mkII". This CPU is slower try fewer reports, or increase SENSOR_US, or reduce BNOs.

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define BNOs        4           // number of BNO08x breakouts connected via TCA9548 mux
#define MPUs        2           // number of MPU6050s connected via TCA9548 mux
#define BNO_MUX_OFFSET 2        // BNOs start at mux port 2
#define pinRST      A3          // output pin to BNO RST

#define MUX_ADDR    0x70        // I2C address of TCA9548 multiplexer
#define TCAADDR     0x70 
#define BNO_ADDR    0x4B        // I2C address of BNO085 sensor (0x4A if SA0=0, 0x4B if SA0=1)
#define I2C_CLOCK   400000L     // I2C clock rate
#define SERIAL_BAUD 230400L     // serial port baud rate
#define SENSOR_US   10000L      // time between sensor reports, microseconds, 10000L is 100 Hz, 20000L is 50 Hz

#define DEBUG       0           // output extra info: 0 off, 1 on. Beware this causes too much output data at low baud rates and/or high sensor rates.

#define ACC_REPORT   0x01   // accel report, see 6.5.9
#define GYRO_REPORT  0x02   // gyro report, see 6.5.13
#define MAG_REPORT   0x03   // magneto report, see 6.5.16
#define LAC_REPORT   0x04   // linear accel report, see 6.5.10
#define QUAT_REPORT  0x05   // quaternion report, see 6.5.18
#define TIME_REPORT  0xFB   // time report, see 7.2.1

Adafruit_MPU6050 mpu[MPUs];
bool bno_printed[BNOs]; 

void tcaselect(uint8_t channel)
{
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

static void request_reports(uint8_t bno)
{
  // Wire.beginTransmission(MUX_ADDR);     // select BNO
  // Wire.write(1 << bno);
  tcaselect(bno + BNO_MUX_OFFSET);
  Wire.endTransmission();

  // request acc reports, see 6.5.4
  static const uint8_t cmd_acc[]  = {21, 0, 2, 0, 0xFD, ACC_REPORT,  0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR);  Wire.write(cmd_acc, sizeof(cmd_acc));  Wire.endTransmission();

  // request gyro reports, see 6.5.4
  static const uint8_t cmd_gyro[] = {21, 0, 2, 0, 0xFD, GYRO_REPORT, 0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR);  Wire.write(cmd_gyro, sizeof(cmd_gyro));  Wire.endTransmission();

  // request magneto reports, see 6.5.4
  static const uint8_t cmd_mag[]  = {21, 0, 2, 0, 0xFD, MAG_REPORT,  0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR);  Wire.write(cmd_mag, sizeof(cmd_mag));  Wire.endTransmission();

  // request linear acc reports, see 6.5.4
  static const uint8_t cmd_lac[]  = {21, 0, 2, 0, 0xFD, LAC_REPORT,  0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR);  Wire.write(cmd_lac, sizeof(cmd_lac));  Wire.endTransmission();

  // request quaternion reports, see 6.5.4
  static const uint8_t cmd_quat[] = {21, 0, 2, 0, 0xFD, QUAT_REPORT, 0, 0, 0, (SENSOR_US>>0)&255, (SENSOR_US>>8)&255, (SENSOR_US>>16)&255, (SENSOR_US>>24)&255, 0, 0, 0, 0, 0, 0, 0, 0};
  Wire.beginTransmission(BNO_ADDR);  Wire.write(cmd_quat, sizeof(cmd_quat));  Wire.endTransmission();

  // At 10ms rate, BNO08x outputs most reports in one burst, Gyro-Quat-Lac-Mag, however Acc is asynchronous and a few percent faster. Situation may vary with SENSOR_US and maximum sensor rates.
}

// *******************
// **  Output data  **
// *******************

int16_t iax[BNOs], iay[BNOs], iaz[BNOs];             // accel, integer
int16_t igx[BNOs], igy[BNOs], igz[BNOs];             // gyro, integer
int16_t imx[BNOs], imy[BNOs], imz[BNOs];             // magneto, integer
int16_t ilx[BNOs], ily[BNOs], ilz[BNOs];             // linear accel, integer
int16_t iqw[BNOs], iqx[BNOs], iqy[BNOs], iqz[BNOs];  // quaternion, integer

char obuf[70], *pbuf;           // ensure this output buffer is big enough for your output string!

void uart_b64(int32_t i)        // output 18-bit integer as compact 3-digit base64
{
  for (int n=12; n >= 0; n-=6)
  {
    uint8_t c = (i >> n) & 63;
    *pbuf++ = (char)(c<26 ? 'A'+c : c<52 ? 'a'-26+c : c<62 ? '0'-52+c : c==62 ? '+' : '/');
  }
}

static void output_data(uint8_t bno)
{
  if (bno_printed[bno]) return;        // skip if already printed this loop
  bno_printed[bno] = true;             // mark as printed

  float kACC = 1.0/9.80665/256;
  float kGYR = 180.0/M_PI/512;
  float kMAG = 0.01/16;
  float kLAC = 1.0/9.80665/256;

  Serial.print("BNO"); Serial.print(bno); Serial.print(" ");
  Serial.print("Acc:");
  Serial.print(kACC*iax[bno],3); Serial.print(",");
  Serial.print(-kACC*iay[bno],3); Serial.print(",");
  Serial.print(-kACC*iaz[bno],3); Serial.print(" ");
  Serial.print("Gyro:");
  Serial.print(kGYR*igx[bno],3); Serial.print(",");
  Serial.print(-kGYR*igy[bno],3); Serial.print(",");
  Serial.print(-kGYR*igz[bno],3); Serial.print(" ");
  Serial.print("Mag:");
  Serial.print(kMAG*imx[bno],3); Serial.print(",");
  Serial.print(-kMAG*imy[bno],3); Serial.print(",");
  Serial.print(-kMAG*imz[bno],3); Serial.print(" ");
  // Serial.print("LinAcc:");
  // Serial.print(kLAC*ilx[bno],3); Serial.print(",");
  // Serial.print(-kLAC*ily[bno],3); Serial.print(",");
  // Serial.print(-kLAC*ilz[bno],3); Serial.print(" ");
  // Serial.print("Quat:");
  // Serial.print(iqw[bno]); Serial.print(",");
  // Serial.print(iqx[bno]); Serial.print(",");
  // Serial.print(iqy[bno]); Serial.print(",");
  // Serial.println(iqz[bno]);
  Serial.println();
}



static void output_mpu(uint8_t idx)
{
  tcaselect(idx);                       // MPUs are on ports 0 and 1

  sensors_event_t accel, gyro, temp;
  mpu[idx].getEvent(&accel, &gyro, &temp);

  Serial.print("MPU"); Serial.print(idx); Serial.print(" ");
  Serial.print("Acc:");
  Serial.print(accel.acceleration.x / 9.80665, 3); Serial.print(",");
  Serial.print(accel.acceleration.y / 9.80665, 3); Serial.print(",");
  Serial.print(accel.acceleration.z / 9.80665, 3); Serial.print(" ");
  Serial.print("Gyro:");
  Serial.print(gyro.gyro.x * 180.0 / M_PI, 3); Serial.print(",");
  Serial.print(gyro.gyro.y * 180.0 / M_PI, 3); Serial.print(",");
  Serial.print(gyro.gyro.z * 180.0 / M_PI, 3); Serial.print(" ");
  // Serial.print("Temp:");
  // Serial.println(temp.temperature, 1);
  Serial.println();
}

// ******************************************
// **  Check for and parse sensor reports  **
// ******************************************

#if DEBUG
  static uint8_t printbyte(uint8_t b)
  {
    Serial.print(" ");  Serial.print(b,HEX);
    return b;
  }
#else
  #define printbyte(b) (b)
#endif

static void ensure_read_available(int16_t length)
{
  if (!Wire.available())
    Wire.requestFrom(BNO_ADDR,4+length), Wire.read(), Wire.read(), Wire.read(), Wire.read();
}

static void check_report(uint8_t bno)
{
  int16_t length;
  uint8_t channel __attribute__((unused));
  uint8_t seqnum  __attribute__((unused));

  tcaselect(bno + BNO_MUX_OFFSET);     // BNOs are on ports 2-5

  Wire.requestFrom(BNO_ADDR,4+1);
  if (DEBUG) {Serial.print("SHTP");}
  length  = printbyte(Wire.read());
  length |= printbyte((Wire.read() & 0x7F) << 8);
  channel = printbyte(Wire.read());
  seqnum  = printbyte(Wire.read());
  length -= 4;
  if (length <= 0 || length > 1000)
  {
    if (DEBUG) {Serial.println(" What?");}
    return;
  }
  if (DEBUG) {Serial.print(" L=");  Serial.print(length,HEX);}
  if (DEBUG) {Serial.print(" C=");  Serial.println(channel,HEX);}

  while (length)
  {
    uint8_t buf[20];
    uint16_t n = 0;

    ensure_read_available(length);
    buf[n++] = printbyte(Wire.read());
    length--;

    if (channel==3 && buf[0]==TIME_REPORT && length >= 5-1)
    {
      for (uint8_t n=1; n<5; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      if (DEBUG) {Serial.println(" Time");}
      continue;
    }
    if (channel==3 && buf[0]==ACC_REPORT && length >= 10-1)
    {
      for (uint8_t n=1; n<10; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      iax[bno] = *(int16_t*)&buf[4];
      iay[bno] = *(int16_t*)&buf[6];
      iaz[bno] = *(int16_t*)&buf[8];
      if (DEBUG) {Serial.println(" Acc");}
      continue;
    }
    if (channel==3 && buf[0]==GYRO_REPORT && length >= 10-1)
    {
      for (uint8_t n=1; n<10; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      igx[bno] = *(int16_t*)&buf[4];
      igy[bno] = *(int16_t*)&buf[6];
      igz[bno] = *(int16_t*)&buf[8];
      if (DEBUG) {Serial.println(" Gyro");}
      continue;
    }
    if (channel==3 && buf[0]==MAG_REPORT && length >= 10-1)
    {
      for (uint8_t n=1; n<10; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      imx[bno] = *(int16_t*)&buf[4];
      imy[bno] = *(int16_t*)&buf[6];
      imz[bno] = *(int16_t*)&buf[8];
      if (DEBUG) {Serial.println(" Mag");}
      output_data(bno);
      continue;
    }
    if (channel==3 && buf[0]==LAC_REPORT && length >= 10-1)
    {
      for (uint8_t n=1; n<10; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      ilx[bno] = *(int16_t*)&buf[4];
      ily[bno] = *(int16_t*)&buf[6];
      ilz[bno] = *(int16_t*)&buf[8];
      if (DEBUG) {Serial.println(" Lac");}
      continue;
    }
    if (channel==3 && buf[0]==QUAT_REPORT && length >= 14-1)
    {
      for (uint8_t n=1; n<14; n++)
      {
        ensure_read_available(length);
        buf[n] = printbyte(Wire.read());
        length--;
      }
      iqw[bno] = *(int16_t*)&buf[10];
      iqx[bno] = *(int16_t*)&buf[4];
      iqy[bno] = *(int16_t*)&buf[6];
      iqz[bno] = *(int16_t*)&buf[8];
      if (DEBUG) {Serial.println(" Quat");}
      continue;
    }

    while (length)
    {
      ensure_read_available(length);
      printbyte(Wire.read());
      length--;
    }
    if (DEBUG) {Serial.println(" Unknown");}
    continue;
  }
  return;
}

// **********************
// **  Setup and Loop  **
// **********************
void setup()
{
  Serial.begin(SERIAL_BAUD);
  Serial.println("\nRunning...");

  pinMode(pinRST,OUTPUT);
  digitalWrite(pinRST,LOW);
  delay(1);
  digitalWrite(pinRST,HIGH);
  delay(300);

  Wire.setSDA(4);
  Wire.setSCL(5);
  Wire.begin();
  Wire.setClock(I2C_CLOCK);
  Serial.println("I2C initialized.");

  // initialize MPU6050s on mux ports 0 and 1
  for (uint8_t i=0; i<MPUs; i++)
  {
    tcaselect(i);
    if (!mpu[i].begin())
    {
      Serial.print("MPU"); Serial.print(i); Serial.println(" not found!");
      while (1) delay(10);
    }
    mpu[i].setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu[i].setGyroRange(MPU6050_RANGE_500_DEG);
    mpu[i].setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.print("MPU"); Serial.print(i); Serial.println(" ready.");
  }

  // initialize BNO085s on mux ports 2-5
  for (uint8_t bno=0; bno<BNOs; bno++)
    request_reports(bno);

  for (uint8_t bno=0; bno<BNOs; bno++)
    do
      check_report(bno);
    while (!iqw[bno] && !iqx[bno] && !iqy[bno] && !iqz[bno]);  
}

void loop()
{
  for (uint8_t i=0; i<BNOs; i++)
    bno_printed[i] = false;            // reset flags

  for (uint8_t i=0; i<MPUs; i++)
    output_mpu(i);

  for (uint8_t bno=0; bno<BNOs; bno++)
    check_report(bno);

  delay(500);
}