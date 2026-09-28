# Raspberry Shake offline demo kit

This kit turns a Mac and a Raspberry Shake connected directly by Ethernet into a self-contained, live seismology demonstration. It does not use the Raspberry Shake cloud, an Internet connection, or any Python packages.

The viewer receives the Shake's local **DATACAST** UDP stream and draws the last two minutes of each channel in real time. An optional 30-second rolling spectrogram shows how signal power is distributed by frequency.

## The portable setup

The recommended arrangement gives every demo Mac the same direct-Ethernet address, `169.254.8.11`. The Shake is configured once to send DATACAST to `169.254.8.11:8888`. After that, any prepared Mac can replace another without changing the Shake.

### Prepare the Shake once

Do this on the owner's Mac while the powered Shake is connected by Ethernet:

1. Double-click **Prepare Raspberry Shake.command**.
2. Approve the Mac network change and enter the Shake's SSH password when prompted.
3. Wait about two minutes for the Shake to reboot.

This enables offline mode and installs the reusable DATACAST destination. It does not need to be repeated on each guest laptop.

### Use it on another Mac

The easiest distribution is a packaged zip from the repository's **Releases** page. Download the Apple Silicon (`arm64`) or Intel (`x86_64`) zip before going offline, unzip it, and then:

1. Connect and power the prepared Shake.
2. Double-click **Start Raspberry Shake Live.command**.
3. Approve the one-time administrator request that sets the active USB Ethernet adapter to `169.254.8.11/16`.
4. The local dashboard opens automatically at `http://127.0.0.1:8765/`.

The packaged release contains a standalone macOS app, so Python is not required. Because the app is not Apple-notarized, the first launch may require Control-clicking the command and choosing **Open**.

To use a source clone instead, install Python 3 and double-click the same start command, or run:

```bash
python3 offline_viewer.py
```

After the demo, while the Ethernet cable is still connected, double-click **Restore Ethernet DHCP.command** to return that adapter to normal automatic addressing.

## One-time setup (do this while you still have Internet)

1. Make sure the Shake has current firmware and change its default SSH password if it still uses one.
2. On the Mac, identify the wired network service manually if automatic detection does not work:

   ```bash
   bash scripts/setup_direct_ethernet_macos.sh --list
   ```

3. Set that service to the isolated direct-connection address. Replace the example service name with the one from the previous command:

   ```bash
   bash scripts/setup_direct_ethernet_macos.sh --service "USB 10/100/1000 LAN"
   ```

   The script asks macOS for administrator approval and assigns `169.254.8.11/16`. This is in the Shake's documented discovery range. It changes only the named wired service; Wi-Fi remains available.

4. Connect the powered Shake directly to that Ethernet port and wait about two minutes for it to boot. Verify that its local name responds:

   ```bash
   ping rs.local
   ```

5. Configure the Shake to send its live stream to the Mac and enable its offline mode:

   ```bash
   bash scripts/configure_shake_for_demo.sh
   ```

   Enter the SSH password when prompted. The script copies the DATACAST destination, sets the Shake clock from the Mac in UTC, enables stand-alone mode, and reboots the Shake. Give it two minutes to restart.

6. Start the local viewer:

   ```bash
   python3 offline_viewer.py
   ```

If macOS asks whether to allow incoming connections, allow Python on private networks. The viewer needs inbound UDP port 8888.

## Demo-day checklist

1. Power the Shake and connect its Ethernet cable directly to the prepared Mac port.
2. Wait until the Shake has booted (normally about two minutes).
3. Run `python3 offline_viewer.py` from this folder.
4. Confirm that the viewer's status changes from **Waiting for UDP data** to **Receiving data**. Gentle taps on the table or floor should produce a visible waveform.
5. Select **Spectrogram: Off** to turn the spectrogram on, then choose the vertical (`EHZ`) or either horizontal (`EHN`/`EHE`) channel.

No Internet connection is required. Keep Wi-Fi off during the demo if you want to demonstrate the fully isolated setup.

## Useful fallback: local Shake web page

With the Ethernet cable connected, `http://rs.local/` is the Shake's own web interface and should remain usable without Internet. Its built-in helicorder is useful for a 12-hour historical view but is not real-time; this kit's viewer is the real-time display.

## Important timing note

Without Internet or an optional GPS receiver, the Shake cannot obtain NTP time. `configure_shake_for_demo.sh` synchronizes its clock to the Mac just before enabling offline mode. If the Shake has been unpowered for a long time before a later demo, rerun that script while directly connected so timestamps are close to current UTC. A GPS receiver provides better timekeeping for long offline deployments.

## Restore ordinary Ethernet networking

After the demo, return the wired service to DHCP:

```bash
bash scripts/setup_direct_ethernet_macos.sh --service "USB 10/100/1000 LAN" --restore-dhcp
```

For the automatic path, use `bash scripts/setup_direct_ethernet_macos.sh --auto --restore-dhcp` while the cable is connected.

## Repository automation

Every push and pull request runs the parser tests. Tags such as `v1.0.0` build two standalone release downloads using GitHub Actions: Apple Silicon (`arm64`) and Intel (`x86_64`). The applications are ad-hoc signed but not Apple-notarized.

## How it works

The Shake's data producer sends compact UDP packets to its own port 8888 by default. The configuration installed by this kit adds a destination on the Mac (`169.254.8.11:8888`). Each packet carries a channel, timestamp, and samples. `offline_viewer.py` listens for that stream locally and plots it; it does not make any outbound connection. The spectrogram uses an in-browser FFT with a Hann window and requires no scientific Python or JavaScript packages.

The configuration is deliberately small and uses only standard-library Python, so it can be tested before travelling and needs no dependency download at the venue.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `rs.local` does not resolve | Confirm the direct Ethernet service is set to `169.254.8.11` and wait for boot. Try `ping 169.254.8.1`; the Shake's permanent discovery address is in `169.254.x.x`, so its exact current address can vary. |
| Viewer remains waiting | Rerun `bash scripts/configure_shake_for_demo.sh`; then ensure macOS Firewall permits inbound UDP for Python. |
| The viewer shows stale / incorrect times | Rerun the configuration script after the Shake has booted. It sets time in UTC before rebooting. |
| Waveforms have periodic RF noise | Keep the Shake on Ethernet; it normally disables Wi-Fi when Ethernet is active. |
| You need a broader analysis tool | The Shake's local SeedLink service is available on port 18000 and its local Winston/OSOP service is port 16032; both work without Internet. |

## Sources

The workflow follows Raspberry Shake's documentation for [offline stand-alone mode](https://manual.raspberryshake.org/no-network.html), [direct Ethernet discovery](https://manual.raspberryshake.org/discoveryIP.html), [DATACAST UDP](https://manual.raspberryshake.org/udp.html), and [local live visualization services](https://manual.raspberryshake.org/traces.html).
