import Foundation
import CoreGraphics

// Real mouse events for apps (like Resolve) that ignore AppleScript "click at".
// usage: click X Y            single click
//        click X Y double     double click
//        click drag X1 Y1 X2 Y2   press at 1, move in steps, release at 2
let a = CommandLine.arguments

func post(_ type: CGEventType, _ p: CGPoint, clicks: Int64 = 1) {
    let e = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: p, mouseButton: .left)!
    e.setIntegerValueField(.mouseEventClickState, value: clicks)
    e.post(tap: .cghidEventTap)
}

if a.count >= 6 && a[1] == "drag" {
    let p1 = CGPoint(x: Double(a[2])!, y: Double(a[3])!)
    let p2 = CGPoint(x: Double(a[4])!, y: Double(a[5])!)
    post(.mouseMoved, p1); usleep(100000)
    post(.leftMouseDown, p1); usleep(100000)
    for i in 1...30 {
        let t = Double(i) / 30
        post(.leftMouseDragged, CGPoint(x: p1.x + (p2.x - p1.x) * t, y: p1.y + (p2.y - p1.y) * t))
        usleep(15000)
    }
    post(.leftMouseUp, p2)
} else {
    let p = CGPoint(x: Double(a[1])!, y: Double(a[2])!)
    let n: Int64 = a.count > 3 ? 2 : 1
    post(.mouseMoved, p); usleep(80000)
    for i in 1...n {
        post(.leftMouseDown, p, clicks: i); usleep(50000)
        post(.leftMouseUp, p, clicks: i); usleep(80000)
    }
}
