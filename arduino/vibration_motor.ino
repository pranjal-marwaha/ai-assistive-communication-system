void setup() { Serial.begin(9600); pinMode(8, OUTPUT); }

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n'); // "V200,0,1"
    if (cmd.startsWith("V")) {
      int on_ms   = cmd.substring(1, cmd.indexOf(',')).toInt();
      int rest    = cmd.indexOf(',') + 1;
      int off_ms  = cmd.substring(rest, cmd.lastIndexOf(',')).toInt();
      int repeats = cmd.substring(cmd.lastIndexOf(',') + 1).toInt();
      for (int i = 0; i < repeats; i++) {
        digitalWrite(8, HIGH); delay(on_ms);
        digitalWrite(8, LOW);  if (off_ms > 0) delay(off_ms);
      }
    }
  }
}