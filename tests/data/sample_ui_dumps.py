"""Sample UI dump data for testing."""

# Sample UI dump from a real Android login screen
LOGIN_SCREEN_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.systemui" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[0,0][1080,1920]">
    <node index="1" text="MyApp" resource-id="com.myapp:id/app_title" class="android.widget.TextView" package="com.myapp" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[340,200][740,280]" />
    <node index="2" text="" resource-id="com.myapp:id/username_field" class="android.widget.EditText" package="com.myapp" content-desc="Enter username" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="true" password="false" selected="false" bounds="[140,400][940,480]" />
    <node index="3" text="" resource-id="com.myapp:id/password_field" class="android.widget.EditText" package="com.myapp" content-desc="Enter password" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="true" password="true" selected="false" bounds="[140,520][940,600]" />
    <node index="4" text="Sign In" resource-id="com.myapp:id/signin_button" class="android.widget.Button" package="com.myapp" content-desc="Sign in to your account" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[240,680][840,760]" />
    <node index="5" text="Forgot Password?" resource-id="com.myapp:id/forgot_password_link" class="android.widget.TextView" package="com.myapp" content-desc="Forgot password link" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[390,800][690,840]" />
  </node>
</hierarchy>"""

# Sample UI dump from a shopping app list
SHOPPING_LIST_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="androidx.recyclerview.widget.RecyclerView" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="true" focused="false" scrollable="true" long-clickable="false" password="false" selected="false" bounds="[0,200][1080,1920]">
    <node index="1" text="" resource-id="" class="android.widget.LinearLayout" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="true" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[20,220][1060,380]">
      <node index="2" text="iPhone 15 Pro" resource-id="com.shopping.app:id/product_title" class="android.widget.TextView" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[120,240][600,280]" />
      <node index="3" text="$999.99" resource-id="com.shopping.app:id/product_price" class="android.widget.TextView" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[120,300][200,330]" />
      <node index="4" text="Add to Cart" resource-id="com.shopping.app:id/add_to_cart_btn" class="android.widget.Button" package="com.shopping.app" content-desc="Add iPhone 15 Pro to cart" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[800,320][1040,360]" />
    </node>
    <node index="5" text="" resource-id="" class="android.widget.LinearLayout" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="true" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[20,400][1060,560]">
      <node index="6" text="Samsung Galaxy S24" resource-id="com.shopping.app:id/product_title" class="android.widget.TextView" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[120,420][650,460]" />
      <node index="7" text="$799.99" resource-id="com.shopping.app:id/product_price" class="android.widget.TextView" package="com.shopping.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[120,480][200,510]" />
      <node index="8" text="Add to Cart" resource-id="com.shopping.app:id/add_to_cart_btn" class="android.widget.Button" package="com.shopping.app" content-desc="Add Samsung Galaxy S24 to cart" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[800,500][1040,540]" />
    </node>
  </node>
</hierarchy>"""

# Sample UI dump with complex nested structure
COMPLEX_NESTED_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.complex.app" bounds="[0,0][1080,1920]">
    <node index="1" text="" resource-id="" class="android.widget.LinearLayout" package="com.complex.app" bounds="[0,0][1080,200]">
      <node index="2" text="Settings" resource-id="com.complex.app:id/toolbar_title" class="android.widget.TextView" package="com.complex.app" bounds="[40,60][200,120]" />
      <node index="3" text="" resource-id="com.complex.app:id/menu_button" class="android.widget.ImageView" package="com.complex.app" content-desc="Menu" clickable="true" bounds="[920,60][1040,120]" />
    </node>
    <node index="4" text="" resource-id="" class="androidx.preference.PreferenceFragmentCompat" package="com.complex.app" scrollable="true" bounds="[0,200][1080,1920]">
      <node index="5" text="" resource-id="" class="androidx.preference.PreferenceCategory" package="com.complex.app" bounds="[0,220][1080,280]">
        <node index="6" text="Account" resource-id="android:id/title" class="android.widget.TextView" package="com.complex.app" bounds="[60,240][150,260]" />
      </node>
      <node index="7" text="" resource-id="" class="androidx.preference.Preference" package="com.complex.app" clickable="true" bounds="[0,300][1080,380]">
        <node index="8" text="Profile" resource-id="android:id/title" class="android.widget.TextView" package="com.complex.app" bounds="[60,320][120,340]" />
        <node index="9" text="View and edit your profile" resource-id="android:id/summary" class="android.widget.TextView" package="com.complex.app" bounds="[60,345][300,365]" />
      </node>
      <node index="10" text="" resource-id="" class="androidx.preference.SwitchPreference" package="com.complex.app" clickable="true" bounds="[0,400][1080,480]">
        <node index="11" text="Dark Mode" resource-id="android:id/title" class="android.widget.TextView" package="com.complex.app" bounds="[60,420][140,440]" />
        <node index="12" text="Enable dark theme" resource-id="android:id/summary" class="android.widget.TextView" package="com.complex.app" bounds="[60,445][200,465]" />
        <node index="13" text="" resource-id="android:id/switch_widget" class="android.widget.Switch" package="com.complex.app" checkable="true" checked="false" clickable="true" bounds="[980,430][1040,450]" />
      </node>
    </node>
  </node>
</hierarchy>"""

# Sample device properties for testing
DEVICE_PROPERTIES = {
    "ro.product.model": "Pixel 7",
    "ro.product.brand": "Google",
    "ro.product.name": "panther",
    "ro.build.version.release": "14",
    "ro.build.version.sdk": "34",
    "ro.product.cpu.abi": "arm64-v8a",
    "ro.hardware": "panther",
    "sys.boot_completed": "1",
    "ro.debuggable": "1",
    "ro.secure": "0",
    "ro.build.type": "user",
    "ro.build.tags": "release-keys",
    "ro.product.locale": "en-US"
}

# Sample logcat entries
SAMPLE_LOGCAT_ENTRIES = [
    "01-01 12:00:01.000  1234  1235 I ActivityManager: Start proc 12345:com.myapp/u0a123 for activity {com.myapp/com.myapp.MainActivity}",
    "01-01 12:00:01.100  1234  1235 I ActivityManager: Activity resumed: com.myapp/.MainActivity",
    "01-01 12:00:01.200 12345 12346 D MyApp: onCreate() called",
    "01-01 12:00:01.300 12345 12346 I MyApp: Loading user preferences",
    "01-01 12:00:01.400 12345 12346 V MyApp: Setting up UI components",
    "01-01 12:00:02.000 12345 12346 D InputMethodManager: showSoftInput",
    "01-01 12:00:03.000 12345 12346 I MyApp: User interaction: button_click",
    "01-01 12:00:03.100  1234  1235 W ActivityManager: Activity pause timeout for ActivityRecord",
    "01-01 12:00:04.000 12345 12346 E MyApp: Network error: Failed to connect to server",
    "01-01 12:00:04.100 12345 12346 W MyApp: Retrying network request (attempt 1/3)"
]

# Error scenarios for testing
ERROR_SCENARIOS = {
    "adb_not_found": {
        "stdout": "",
        "stderr": "adb: command not found",
        "return_code": 127
    },
    "device_offline": {
        "stdout": "List of devices attached\nemulator-5554\toffline\n",
        "stderr": "",
        "return_code": 0
    },
    "unauthorized_device": {
        "stdout": "List of devices attached\nemulator-5554\tunauthorized\n",
        "stderr": "",
        "return_code": 0
    },
    "ui_service_error": {
        "stdout": "",
        "stderr": "ERROR: could not get idle state.",
        "return_code": 1
    },
    "permission_denied": {
        "stdout": "",
        "stderr": "adb: permission denied",
        "return_code": 1
    },
    "timeout_error": {
        "stdout": "",
        "stderr": "timeout: failed to connect",
        "return_code": 124
    }
}