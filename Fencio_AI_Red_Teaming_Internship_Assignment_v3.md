

<!-- Start of picture text -->
Giencio...<br><!-- End of picture text -->

# **AI Security Engineering Internship Assignment** 

Build an AI Agent Red Teaming System for Autonomous Security Testing 

**This assignment evaluates practical ability across AI/ML, agent engineering, offensive security, AI security testing, and product engineering.** 

## **1. Objective** 

Build a working prototype of an AI security red teaming system that can autonomously assess another AI agent for security vulnerabilities. Your system should use a custom-trained, fine-tuned, or otherwise adapted offensive AI model and build an AI agent around that model. 

The final system should interact with a target AI agent, execute security tests, identify vulnerabilities, collect evidence, and produce a structured security assessment. 

## **2. Problem Statement** 

AI agents can be vulnerable to prompt injection, indirect prompt injection, jailbreaks, system prompt extraction, instruction hierarchy manipulation, sensitive information disclosure, tool abuse, excessive agency, insecure tool usage, privilege escalation, context manipulation, data exfiltration, memory poisoning, and unsafe behavior caused by malicious external content. 

Your task is to build an autonomous security assessment system that can discover and demonstrate these types of weaknesses in a controlled AI agent. 

## **3. What You Need To Build** 

### **3.1 Offensive AI Model** 

Select an open-source model from Hugging Face or another publicly available source. You should either fine-tune an existing model, train it further using your own security dataset, or adapt an existing model specifically for AI security testing. 

- Optimize the model for generating, reasoning about, or evaluating adversarial security tests against AI agents. 

- Use training or fine-tuning data relevant to prompt injection, jailbreaks, information extraction, tool abuse, and similar attacks. 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 1 

- Document the base model, why it was selected, dataset, dataset structure, training or fine-tuning methodology, parameters, evaluation methodology, and limitations. 

### **3.2 AI Red Teaming Agent** 

Build an AI agent around your offensive model. It should be able to: 

- Discover or understand the capabilities of a target AI agent. 

- Identify potential attack surfaces. 

- Generate security test cases. 

- Send test cases to the target. 

- Analyze target responses. 

- Decide whether additional testing is required. 

- Attempt different attack strategies based on observed behavior. 

- Identify successful or suspicious behaviors. 

- Record evidence. 

- Produce a final security assessment. 

The system should not simply execute a static list of prompts. We want to see some degree of **autonomous decision making** . 

### **Suggested Assessment Flow** 

```
Target Agent
     |
     v
Reconnaissance
     |
     v
Attack Surface Identification
     |
     v
Attack Generation
     |
     v
Attack Execution
     |
     v
Response Analysis
     |
     v
Potential Vulnerability?
   /             \
 Yes              No
 |                |
 v                v
Collect        Generate New
Evidence       Attack Strategy
   \             /
    \           /
     v         v
      Assessment
          |
          v
    Security Report
```

### **3.3 Target AI Agent** 

You may use an intentionally vulnerable AI agent as your target. One suggested target is **Damn Vulnerable AI Agent by Opena2a.org** . 

Repository: github.com/opena2a-org/damn-vulnerable-ai-agent 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 2 

You are free to select another open-source AI agent as long as you can demonstrate its architecture and security attack surface. The target should ideally contain multiple capabilities such as LLM interaction, tools, external APIs, file access, web access, memory, RAG, database interaction, or agent-to-tool communication. 

#### **Document the target architecture before testing it.** 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 3 

## **4. Minimum Security Tests** 

Your red teaming agent should attempt to identify at least **five different classes of AI security vulnerabilities** . At minimum, include: 

### **Prompt Injection** 

Attempt to manipulate the agent into ignoring its original instructions and following attacker-controlled instructions. 

### **System Prompt Extraction** 

Determine whether sensitive system instructions or hidden configuration can be extracted. 

### **Indirect Prompt Injection** 

Introduce attacker-controlled instructions through external content such as a webpage, document, or other data source. 

### **Sensitive Information Disclosure** 

Determine whether the target can be manipulated into revealing information it should not disclose. 

### **Tool Abuse / Excessive Agency** 

Test whether the agent can be manipulated into performing actions through its tools that exceed its intended authorization. 

## **5. Autonomous Attack Loop** 

A major part of the assignment is demonstrating that your system can adapt its attacks based on what it observes. 

### **Example attack loop** 



<!-- Start of picture text -->
ATTACK 01<br>  |<br>  v<br>Target Response<br>  |<br>  v<br>Model analyzes response<br>  |<br>  v<br>Potential vulnerability?<br>  |<br>  +-------------------+<br>  |                   |<br> YES                  NO<br>  |                   |<br>  v                   v<br>Collect evidence   Generate a<br>  |                new strategy<br>  |                   |<br>  +---------+---------+<br>            |<br>            v<br>       Execute next test<br>            |<br>            v<br>     Confirm or reject<br>       the finding<br><!-- End of picture text -->

The agent should maintain an assessment state throughout the engagement. It should know what has already been tested, what succeeded, what failed, what attack should be attempted next, which vulnerabilities have been confirmed, and what evidence has been collected. 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 4 

## **6. Security Assessment Output** 

At the end of an assessment, your system should automatically generate a report. 

- **Executive Summary:** Overall security posture of the target. 

- **Vulnerabilities:** For each finding, include vulnerability name, severity, description, attack category, attack methodology, evidence, target response, impact, reproduction information, and recommended remediation. 

### **Example finding** 

|**FINDING**|Indirect Prompt Injection|
|---|---|
|**SEVERITY**|**High**|
|**DESCRIPTION**|The agent follows attacker-controlled instructions contained inside externally retrieved<br>content.|
|**EVIDENCE**|[Relevant interaction / evidence]|
|**IMPACT**|An attacker may influence the agent's behavior through untrusted external content.|
|**RECOMMENDATIO**<br>**N**|Treat externally retrieved content as untrusted input and enforce instruction boundaries before<br>execution.|



## **8. Required Deliverables** 

### **Source Code** 

Complete GitHub repository containing model training or fine-tuning code, dataset preparation, agent implementation, target integration, security testing framework, reporting system, configuration, and README. 

### **Trained / Adapted Model** 

Provide instructions for reproducing the model or provide the checkpoint where licensing permits. 

### **Dataset** 

Provide the dataset created or used for training or fine-tuning, with its source and licensing information. 

### **Technical Documentation** 

Explain architecture, model selection, training process, agent design, attack methodology, detection methodology, and limitations. 

### **Demonstration** 

Record a 10 to 15 minute demo showing the system performing an assessment against the target. The demo should show actual assessment activity, not only pre-generated results. 

### **Final Security Report** 

Generate an actual report from your tool against the selected target. 

## **9. Expected Runtime Output** 

Your system should produce a clear, readable assessment log while the engagement is running. The following is an example of the type of output expected: 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 5 

```
Target: Vulnerable AI Agent
Starting Security Assessment...
[+] Reconnaissance complete
Attack Surface:
    LLM
    Web Tool
    File Tool
    Memory
    External Content
[+] Starting Prompt Injection Tests
    Test 01 ........................ FAILED
    Test 02 ........................ FAILED
    Test 03 ........................ SUCCESS
[!] Potential Prompt Injection Found
[+] Generating follow-up attack...
    Follow-up Test ................. SUCCESS
[+] Vulnerability Confirmed
[+] Starting Tool Abuse Tests
    Test 01 ........................ SUCCESS
[!] Potential Tool Abuse Found
Assessment Complete
Critical: 1
High: 2
Medium: 3
Low: 1
Report generated.
```

## **10. Constraints** 

- Use only systems that you own, have permission to test, or are intentionally vulnerable targets. 

- Do not test public production AI systems without explicit authorization. 

- Open-source models, datasets, and tools may be used, but clearly document what you used and what you built yourself. 

- Do not simply wrap an existing red teaming framework and submit it as your own implementation. 

- Third-party components may be used where appropriate, but the core offensive reasoning and assessment workflow should be your implementation. 

## **11. Bonus Points** 

- Multi-agent red teaming architecture 

- Adaptive attack generation 

- Attack strategy planning 

- Automated vulnerability verification 

- Severity scoring 

- Attack replay 

- Attack history and memory 

- RAG security testing 

- Agent memory poisoning tests 

- Tool authorization testing 

- Browser-agent security testing 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 6 

- Multi-turn attack chains 

- Detection of previously unknown attack patterns 

- Comparison against existing AI security testing tools 

- Quantitative evaluation of attack success rate 

- Measurement of false positives and false negatives 

## **12. Final Question** 

**If you were building this into a production-grade AI security product for enterprise customers, what would you change about your architecture?** 

We are interested not only in whether the prototype works, but also in how you think about turning an experimental security tool into a reliable product. 

## **13. Expected Outcome** 

The final result should demonstrate that you can independently build an **AI-powered offensive security system capable of assessing another AI agent, adapting its attack strategy, identifying vulnerabilities, collecting evidence, and producing a meaningful security assessment.** 

|**AI / ML**|Model selection, adaptation, fine-tuning, evaluation, and understanding of model limitations.|
|---|---|
|**Agent Engineering**|Autonomous workflow, state management, tool use, attack planning, and response<br>analysis.|
|**Offensive Security**|Ability to reason about AI attack surfaces and demonstrate vulnerabilities safely against<br>controlled targets.|
|**Product Engineering**|Reproducibility, clean implementation, useful output, documentation, and a path toward a<br>production system.|



**What matters most: We are looking for evidence that you can independently take a security problem, build a working AI system around it, test it against a real controlled target, and explain why your findings are valid.** 

Fencio.dev | AI Security Engineering Internship Assignment 

Page 7 

