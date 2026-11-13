package main

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"time"
)

func memoryPressure() {
	chunks := make([][]byte, 0, 64)
	for {
		block := make([]byte, 4*1024*1024)
		for i := 0; i < len(block); i += 4096 {
			block[i] = 1
		}
		chunks = append(chunks, block)
		time.Sleep(10 * time.Millisecond)
	}
}

func cpuPressure() {
	runtime.GOMAXPROCS(1)
	for {
	}
}

func pidPressure() {
	children := make([]*exec.Cmd, 0, 128)
	for i := 0; i < 1024; i++ {
		cmd := exec.Command(os.Args[0], "child")
		if err := cmd.Start(); err != nil {
			fmt.Println("PID_LIMIT_REACHED")
			time.Sleep(250 * time.Millisecond)
			return
		}
		children = append(children, cmd)
	}
	fmt.Println("PID_LIMIT_NOT_REACHED")
	os.Exit(2)
}

func child() {
	time.Sleep(60 * time.Second)
}

func main() {
	runtime.GOMAXPROCS(1)

	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "mode required")
		os.Exit(2)
	}

	switch os.Args[1] {
	case "memory":
		memoryPressure()
	case "cpu":
		cpuPressure()
	case "pids":
		pidPressure()
	case "child":
		child()
	default:
		fmt.Fprintln(os.Stderr, "unknown mode")
		os.Exit(2)
	}
}
